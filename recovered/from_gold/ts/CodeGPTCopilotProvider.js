const { InlineCompletionItem, Range } = require("vscode");

const vscode = require("vscode");
const { sendEvent } = require("./utils/telemetry");
const axios = require("axios");
const { getDistinctId, getSession } = require("./utils/distinctId");

const DEFAULT_NUM_WARNINGS = 3;
const DEFAULT_DEBOUNCE_MS = 150;
const LOCAL_CACHE_LIMIT = 500;
const LOCAL_CACHE_KEY_CHARS = 200;
const N_CHARS_CACHE = 20;

const nextjsPort = 54113;
let timerId;
const currentCancelToken = axios.CancelToken.source();
let numWarnings = DEFAULT_NUM_WARNINGS;
let lastWarningMessage = "";

console.debug = () => {};

class LocalCompletionCache {
	constructor(limit = LOCAL_CACHE_LIMIT) {
		this.cache = new Map();
		this.limit = limit;
	}

	_hash(prefix, suffix) {
		const p = prefix.slice(-LOCAL_CACHE_KEY_CHARS);
		const s = suffix.slice(0, LOCAL_CACHE_KEY_CHARS);
		return `${p}\u0000${s}`;
	}

	_evict() {
		while (this.cache.size > this.limit) {
			const firstKey = this.cache.keys().next().value;
			if (!firstKey) break;
			this.cache.delete(firstKey);
		}
	}

	get(prefix, suffix) {
		const key = this._hash(prefix, suffix);
		const entry = this.cache.get(key);
		if (!entry) return null;
		// LRU touch
		this.cache.delete(key);
		this.cache.set(key, entry);
		return entry;
	}

	set(prefix, suffix, completion, autocompleteId, indexSuffix, provider, model) {
		const text = prefix + completion;
		// Forward variants (typed-through)
		const forwardMax = Math.min(text.length, prefix.length + N_CHARS_CACHE);
		for (let i = prefix.length; i < forwardMax; i++) {
			const newPrefix = text.slice(0, i);
			const newCompletion = text.slice(i);
			this.cache.set(this._hash(newPrefix, suffix), {
				text: newCompletion,
				autocompleteId,
				indexSuffix,
				provider,
				model,
			});
		}
		// Backward variants (backspace-aware)
		const backMin = Math.max(0, prefix.length - N_CHARS_CACHE);
		for (let i = prefix.length - 1; i >= backMin; i--) {
			const charsRemoved = prefix.length - i;
			const newPrefix = prefix.slice(0, i);
			const newCompletion =
				prefix.slice(i) + completion.slice(0, Math.max(0, completion.length - charsRemoved));
			if (!newCompletion) continue;
			this.cache.set(this._hash(newPrefix, suffix), {
				text: newCompletion,
				autocompleteId,
				indexSuffix: -1, // recalcular en VS Code si hace falta
				provider,
				model,
			});
		}
		this._evict();
	}

	clear() {
		this.cache.clear();
	}
}

const localCache = new LocalCompletionCache();

class HealthMetrics {
	constructor() {
		this.reset();
	}

	reset() {
		this.requests = 0;
		this.cacheHits = 0;
		this.cancelled = 0;
		this.errors = 0;
		this.latencies = [];
		this.acceptances = 0;
	}

	record({ latencyMs, cacheHit, cancelled, error }) {
		this.requests += 1;
		if (cacheHit) this.cacheHits += 1;
		if (cancelled) this.cancelled += 1;
		if (error) this.errors += 1;
		if (typeof latencyMs === "number" && !cancelled && !error) {
			this.latencies.push(latencyMs);
			if (this.latencies.length > 500) this.latencies.shift();
		}
	}

	recordAccept() {
		this.acceptances += 1;
	}

	_percentile(p) {
		if (this.latencies.length === 0) return 0;
		const sorted = [...this.latencies].sort((a, b) => a - b);
		const idx = Math.min(sorted.length - 1, Math.floor(p * sorted.length));
		return sorted[idx];
	}

	snapshot() {
		const r = this.requests || 1;
		return {
			requests: this.requests,
			cacheHitRate: +(this.cacheHits / r).toFixed(3),
			cancelRate: +(this.cancelled / r).toFixed(3),
			errorRate: +(this.errors / r).toFixed(3),
			acceptances: this.acceptances,
			acceptRate: +(this.acceptances / r).toFixed(3),
			p50: this._percentile(0.5),
			p95: this._percentile(0.95),
			p99: this._percentile(0.99),
		};
	}
}

const healthMetrics = new HealthMetrics();

const NEIGHBOR_MAX_TABS = 5;
const NEIGHBOR_MAX_CHARS_PER_FILE = 2000;
const NEIGHBOR_TIMEOUT_MS = 50;

// Capture content from open tabs (other than the active one) to enrich
// cross-file context. Capped in count, size and elapsed time so it never
// becomes a latency hot path.
async function collectNeighborSnippets(activeUri) {
	const startedAt = Date.now();
	try {
		const tabs = vscode.window.tabGroups?.all
			?.flatMap((g) => g.tabs)
			?.filter(
				(t) =>
					t?.input?.uri &&
					t.input.uri.path !== activeUri?.path &&
					t.input.uri.scheme === "file",
			) ?? [];

		// Most-recent-first: VS Code keeps active tab last in the list, so reverse
		const candidates = tabs.slice().reverse().slice(0, NEIGHBOR_MAX_TABS);

		const snippets = await Promise.all(
			candidates.map(async (tab) => {
				if (Date.now() - startedAt > NEIGHBOR_TIMEOUT_MS) return null;
				try {
					const doc = await vscode.workspace.openTextDocument(tab.input.uri);
					const content = doc.getText().slice(0, NEIGHBOR_MAX_CHARS_PER_FILE);
					return {
						fileName: doc.fileName.split("/").pop(),
						languageId: doc.languageId,
						content,
					};
				} catch {
					return null;
				}
			}),
		);

		return snippets.filter(Boolean);
	} catch {
		return [];
	}
}

function getIndexSuffix(text, prompt) {
	const firstSuffixLine = prompt.suffix.split("\n")[0];
	const leadingSpaces = firstSuffixLine.match(/^\s*/) ?? [""];
	let indexSuffix = -1;

	if (prompt.suffix) {
		// Check if the first part of the choiceText matches the first suffix line
		if (!/^[\t\n]/.test(prompt.suffix)) {
			// Start from the right, until leading spaces are reached
			for (let i = firstSuffixLine.length; i > leadingSpaces[0].length; i--) {
				indexSuffix = text.indexOf(firstSuffixLine.slice(0, i));
				// If a match is found, return the index
				if (indexSuffix >= 0) {
					return indexSuffix;
				}
			}
		}
	}
	return indexSuffix;
}

class CodeGPTCopilotProvider {
	log;
	requestStatus = "done";
	statusBar;
	currentRequestId = 0;

	constructor(statusBar, logger, context) {
		this.statusBar = statusBar;
		this.log = logger;
		this.context = context;
		this.lastDocumentText = "";
		this.lastCompletion = [];
		this.lastCompletionStartPosition = null;
		this.userTypedText = "";
		this.lastCompletionTranslation = -1;
		this.lastProvider = "";
		this.currentAbortController = null;
	}

	getMetrics() {
		return healthMetrics.snapshot();
	}

	recordAccept(autocompleteId) {
		healthMetrics.recordAccept(autocompleteId);
	}

	clearLocalCache() {
		localCache.clear();
	}

	// @ts-expect-error
	// because ASYNC and PROMISE
	async provideInlineCompletionItems(document, position) {
		this.currentRequestId += 1;
		const requestId = this.currentRequestId;
		const startTime = Date.now();

		// Cancel any in-flight request — its result would be stale
		if (this.currentAbortController) {
			try {
				this.currentAbortController.abort();
			} catch {}
		}
		this.currentAbortController = new AbortController();
		const abortSignal = this.currentAbortController.signal;

		if (!(await this.context.globalState.get("autocompleteEnabled"))) {
			this.log("Extension not enabled, skipping.");
			return Promise.resolve([]);
		}
		const documentText = document.getText();
		const cursorPosition = document.offsetAt(position);

		if (this.lastDocumentText === documentText) {
			this.log("Document text is the same, skipping.");
			return Promise.resolve(this.lastCompletion ? this.lastCompletion : []);
		}

		this.lastDocumentText = documentText;

		// Calculate typed text since last completion was provided
		if (this.lastCompletionStartPosition && this.lastCompletion.length > 0) {
			const typedText = documentText.slice(
				this.lastCompletionStartPosition,
				cursorPosition,
			);

			const insertedText = this.lastCompletion[0].insertText;
			if (typedText && insertedText.startsWith(typedText)) {
				this.userTypedText = typedText;

				// Calculate the remaining text that hasn't been typed yet
				const remainingText = insertedText.slice(typedText.length);

				const actualChar = typedText.slice(-1);
				const nextChar = documentText.slice(
					this.lastCompletionStartPosition + typedText.length,
					cursorPosition + 1,
				);
				if (
					["'", "`", '"', "}", "]", ")"].includes(nextChar) &&
					["'", "`", '"', "{", "[", "("].includes(actualChar)
				) {
					const indexSuffix = getIndexSuffix(remainingText, {
						suffix: nextChar,
					});
					// If the first part of text matches the first suffix line
					if (indexSuffix >= 0) {
						// translate the position according to that index
						this.lastCompletionTranslation = remainingText.length - indexSuffix;
					}
				}

				if (remainingText) {
					// Sanitize: strip leading blank lines and drop whitespace-only
					// continuations — they render as empty inserted lines.
					let cleanRemaining = remainingText;
					if (!cleanRemaining.trim()) {
						cleanRemaining = "";
					} else if (/^\n\s*\n/.test(cleanRemaining)) {
						cleanRemaining = cleanRemaining.replace(/^\n+/, "");
						if (!cleanRemaining.trim()) cleanRemaining = "";
					}

					if (cleanRemaining && cleanRemaining.trim()) {
						// Always pure-insert: never use a replace-range here. Stored
						// `lastCompletionTranslation` reflected the old completion's
						// bracket overlap, which doesn't apply to the trimmed remainder.
						const range = new vscode.Range(position, position);
						const newCompletion = new vscode.InlineCompletionItem(
							cleanRemaining,
							range,
							{
								title: "CodeGPT.onCompletionAccepted",
								command: "codegpt.onCompletionAccepted",
								arguments: [
									cleanRemaining,
									true,
									this.lastAutocompleteId,
								],
							},
						);

						return Promise.resolve([newCompletion]);
					}
				}
			}
		}

		// Reset lastCompletion for the new request
		this.lastCompletion = [];
		this.lastCompletionStartPosition = cursorPosition;
		this.lastCompletionTranslation = -1;

		if (timerId) {
			clearTimeout(timerId);
		}

		// Try local cache before scheduling a network request
		const localPrefix = documentText.slice(0, cursorPosition);
		const localSuffix = documentText.slice(cursorPosition);
		const cached = localCache.get(localPrefix, localSuffix);
		if (cached && cached.text) {
			let cachedText = cached.text;
			let cachedIndexSuffix = cached.indexSuffix;

			// Apply same sanitation as the live path: strip leading blank lines,
			// drop pure-whitespace completions, and invalidate indexSuffix if we
			// mutated the text (otherwise VS Code paints a phantom delete range).
			let cachedMutated = false;
			if (!cachedText.trim()) {
				cachedText = "";
			} else if (/^\n\s*\n/.test(cachedText)) {
				cachedText = cachedText.replace(/^\n+/, "");
				cachedMutated = true;
				if (!cachedText.trim()) cachedText = "";
			}

			// Pure-insert: trim trailing bracket overlap into the text instead
			// of using a replace-range, so VS Code never paints a delete marker.
			if (
				cachedText &&
				!cachedMutated &&
				cachedIndexSuffix >= 0 &&
				cachedIndexSuffix < cachedText.length
			) {
				cachedText = cachedText.slice(0, cachedIndexSuffix);
			}

			if (cachedText && cachedText.trim()) {
				const replaceRange = new Range(position, position);
				const completion = [
					new InlineCompletionItem(cachedText, replaceRange, {
						title: "CodeGPT.onCompletionAccepted",
						command: "codegpt.onCompletionAccepted",
						arguments: [cachedText, true, cached.autocompleteId],
					}),
				];
				this.lastCompletion = completion;
				this.lastCompletionTranslation = 0;
				healthMetrics.record({
					latencyMs: Date.now() - startTime,
					cacheHit: true,
					cancelled: false,
					error: false,
				});
				return Promise.resolve(completion);
			}
		}

		const configuredDelay = await this.context.globalState.get(
			"autocompleteSuggestionDelay",
		);
		const delay =
			typeof configuredDelay === "number" && configuredDelay >= 0
				? configuredDelay
				: DEFAULT_DEBOUNCE_MS;

		return new Promise((resolve) => {
			timerId = setTimeout(async () => {
				if (requestId !== this.currentRequestId) {
					healthMetrics.record({ cancelled: true });
					return resolve([]);
				}

				// Autocomplete for commits
				const isSCM = document.languageId === "scminput";

				const language = vscode.env.language;

				this.requestStatus = "pending";
				this.statusBar.text = "$(codegpt-logotype) $(loading~spin)";
				this.statusBar.tooltip = "CodeGPT - Working 👌";
				let completionProvider = "";

				try {
					const neighborSnippets = await collectNeighborSnippets(document.uri);
					if (requestId !== this.currentRequestId) {
						healthMetrics.record({ cancelled: true });
						return resolve([]);
					}

					const response = await fetch(
						`http://localhost:54112/${nextjsPort}/api/autocomplete`,
						{
							method: "POST",
							signal: abortSignal,
							headers: {
								"Content-Type": "application/json",
								referer: `http://localhost:54112/${nextjsPort}`,
							},
							body: JSON.stringify({
								text: documentText,
								positionLine: position.line,
								positionChar: position.character,
								fileName: document.fileName.split("/").pop(),
								language: document.languageId,
								workspacePath:
									vscode.workspace.workspaceFolders?.[0].uri.path ?? ".",
								isSCM,
								neighborSnippets,
							}),
						},
					);

					let { text, indexSuffix, autocompleteId, model, provider, error } =
						await response.json();
					// const autocompleteProvider = await context.globalState.get(`autocompleteProvider`)
					// const autocompleteModel = await context.globalState.get(`autocompleteModel`)
					// update model and provider
					this.context.globalState.update("autocompleteProvider", provider);
					this.context.globalState.update("autocompleteModel", model);

					completionProvider = provider;
					if (this.lastProvider !== provider)
						numWarnings = DEFAULT_NUM_WARNINGS;
					this.lastProvider = provider;

					this.log(
						`completion provider = ${completionProvider} | model = ${model}`,
					);

					if (error) {
						if (error.includes("Ollama aborted by the user"))
							return resolve([]);
						throw Error(error);
					}

					// Defensive: drop completions that are only whitespace/newlines,
					// or that lead with multiple blank lines — they render as a
					// gap of empty inserted lines and look broken to the user.
					let textWasModified = false;
					if (text) {
						if (!text.trim()) {
							text = "";
						} else if (/^\n\s*\n/.test(text)) {
							// Strip leading blank lines but keep the rest
							text = text.replace(/^\n+/, "");
							textWasModified = true;
							// If after stripping there's still no real content, drop it
							if (!text.trim()) text = "";
						}
					}

					if (text) {
						// If the suggestion would overlap with a closing bracket on the
						// same line (e.g. cursor inside `()` and suggestion ends with `)`),
						// trim the trailing overlap from the text instead of using a
						// replace-range. This keeps the completion as a pure insert and
						// avoids confusing red/green ghost-text rendering.
						if (indexSuffix >= 0 && !textWasModified && indexSuffix < text.length) {
							text = text.slice(0, indexSuffix);
						}
					}
					if (text && text.trim()) {
						const replaceRange = new Range(position, position);
						const lastCompletionTranslation = 0;
						const completion = [
							new InlineCompletionItem(text, replaceRange, {
								title: "CodeGPT.onCompletionAccepted",
								command: "codegpt.onCompletionAccepted",
								arguments: [text, true, autocompleteId],
							}),
						];
						if (requestId === this.currentRequestId) {
							// Write to local cache for backspace/typed-through reuse
							localCache.set(
								localPrefix,
								localSuffix,
								text,
								autocompleteId,
								indexSuffix ?? -1,
								provider,
								model,
							);
							resolve(completion);
							this.lastCompletion = completion;
							this.lastCompletionTranslation = lastCompletionTranslation;
							healthMetrics.record({
								latencyMs: Date.now() - startTime,
								cacheHit: false,
								cancelled: false,
								error: false,
							});
							await this.sendEventWithStatusCode({
								statusCode: 200,
								completionProvider,
								model,
								language,
								autocompleteId,
								codeLinesNumber: text.split("\n").length,
							});
						} else {
							healthMetrics.record({ cancelled: true });
							resolve([]);
						}
					} else {
						healthMetrics.record({
							latencyMs: Date.now() - startTime,
							cacheHit: false,
							cancelled: false,
							error: false,
						});
					}
					this.statusBar.text = "$(codegpt-logotype)";
					this.statusBar.tooltip = "CodeGPT - Ready";
				} catch (error) {
					if (error?.name === "AbortError") {
						healthMetrics.record({ cancelled: true });
						return resolve([]);
					}
					healthMetrics.record({
						latencyMs: Date.now() - startTime,
						cacheHit: false,
						cancelled: false,
						error: true,
					});
					if (
						error.message.includes("Request timed out") &&
						completionProvider == "Ollama"
					) {
						// Close on timeout for Ollama since this could be related to loading the model
						return resolve([]);
					}
					let tooltipMessage = "";
					switch (completionProvider) {
						case "Ollama":
							tooltipMessage = "Make sure the Ollama URL is set correctly";
							break;
						case "Mistral":
							tooltipMessage = "Make sure the Mistral API Key is set correctly";
							break;
						default:
							tooltipMessage =
								error.message === "AUTOCOMPLETE_LIMIT_REACHED"
									? "Autocomplete limit reached"
									: "Something went wrong";
							break;
					}
					if (error.message === "Invalid access token")
						tooltipMessage = "You must log in to use CodeGPT Plus as provider";
					if (error.message.includes("try pulling it first")) {
						const modelRegex = /model\s+"([^"]+)"/;
						const match = error.message.match(modelRegex);
						if (match) {
							const model = match[1];
							tooltipMessage = `You must download the ${model} in Ollama first`;
						} else {
							tooltipMessage =
								"You must download the selected model in Ollama first";
						}
					}
					if (numWarnings > 0 && lastWarningMessage !== tooltipMessage) {
						if (error.message === "AUTOCOMPLETE_LIMIT_REACHED") {
							vscode.window
								.showInformationMessage(
									"You have reached the limit of autocompletes. Upgrade to pro to get more.",
									{
										modal: false,
										detail:
											"You have reached the limit of autocompletes. Upgrade to pro to get more.",
									},
									"Upgrade",
								)
								.then((selection) => {
									if (selection === "Upgrade") {
										vscode.env.openExternal(
											vscode.Uri.parse(
												"https://app.codegpt.co/en/extensions/plans?utm_source=reach-limit",
											),
										);
									}
								});
						} else {
							vscode.window
								.showInformationMessage(
									"We're experiecing high demand for autocomplete right now. please upgrade to pro, or try again in a few moments.",
									{
										modal: false,
										detail:
											"We're experiecing high demand for autocomplete right now. please upgrade to pro, or try again in a few moments.",
									},
									"Upgrade",
								)
								.then((selection) => {
									if (selection === "Upgrade") {
										vscode.env.openExternal(
											vscode.Uri.parse(
												"https://app.codegpt.co/en/extensions/plans?utm_source=vscode-extension&utm_medium=in-app&utm_campaign=rate-limit-upgrade",
											),
										);
									}
								});
						}
					}
					lastWarningMessage !== tooltipMessage && numWarnings <= 0
						? (numWarnings = DEFAULT_NUM_WARNINGS)
						: numWarnings--;
					lastWarningMessage = tooltipMessage;
					this.log(`${error.message}: ${tooltipMessage}`);
					this.statusBar.text = "$(codegpt-logotype) $(alert)";
					this.statusBar.tooltip = `CodeGPT - ${tooltipMessage}`;
					resolve([]);
				} finally {
					this.requestStatus = "done";
				}
			}, delay);
		});
	}

	sleep(milliseconds) {
		// eslint-disable-next-line promise/param-names
		return new Promise((r) => setTimeout(r, milliseconds));
	}

	async sendEventWithStatusCode({
		statusCode,
		completionProvider,
		autocompleteId,
		model,
		language,
		codeLinesNumber,
	}) {
		const codeGPTVersion = this.context.extension.packageJSON.version;
		const codeGPTUserId = await getDistinctId();
		const codeLanguage = vscode.window.activeTextEditor.document.languageId;

		let accessToken;
		try {
			const session = await getSession();
			accessToken = JSON.parse(session)?.accessToken;
		} catch {}

		const mixPanelData = {
			userType: !accessToken ? "anonymous" : "registered",
			provider: completionProvider,
			model,
			codeLinesNumber,
			autocompleteId,
			language,
			codeLanguage,
			codeGPTVersion,
		};

		const signedDistinctId = await getSession().then(
			(session) => session?.signedDistinctId,
		);
		const fullData = {
			...mixPanelData,
			statusCode,
		};
		sendEvent(
			"Autocomplete",
			fullData,
			codeGPTUserId,
			accessToken,
			signedDistinctId,
		);
	}
}

module.exports = CodeGPTCopilotProvider;
