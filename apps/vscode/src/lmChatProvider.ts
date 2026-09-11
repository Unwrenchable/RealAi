import * as vscode from 'vscode';
import { RealAIClient, ChatMessage } from './realaiClient';
import { buildContextSnapshot } from './contextPack';
import { collectStackSnapshot } from './stackStatus';
import { auditAppsVscode } from './extensionAudit';
import { buildStageBrief } from './stageContext';

export const REALAI_LM_VENDOR = 'realai';
const DEFAULT_CONTEXT_TOKENS = 65536;
const AGENT_PREFIX = 'agent:';
const CODER_FULLSTACK_ID = 'realai:coder-fullstack';

function estimateTokens(messages: readonly ChatMessage[]): number {
  return messages.reduce((total, message) => total + Math.ceil(message.content.length / 4) + 4, 0);
}

export function fitMessagesToContext(
  messages: readonly ChatMessage[],
  contextTokens: number,
  outputReserve = 512
): ChatMessage[] {
  const budget = Math.max(512, contextTokens - outputReserve);
  const fitted = messages.map((message) => ({ ...message }));

  while (fitted.length > 1 && estimateTokens(fitted) > budget) {
    const removableIndex = fitted.findIndex(
      (message, index) => index < fitted.length - 1 && message.role !== 'system'
    );
    if (removableIndex < 0) break;
    fitted.splice(removableIndex, 1);
  }

  if (estimateTokens(fitted) > budget && fitted.length) {
    const last = fitted[fitted.length - 1];
    const availableChars = Math.max(128, (budget - 4) * 4);
    fitted[fitted.length - 1] = {
      ...last,
      content: last.content.slice(-availableChars),
    };
  }

  return fitted;
}

function toRealAIRole(role: vscode.LanguageModelChatMessageRole): ChatMessage['role'] {
  return role === vscode.LanguageModelChatMessageRole.Assistant ? 'assistant' : 'user';
}

function extractText(content: ReadonlyArray<unknown>): string {
  return content
    .filter((part): part is vscode.LanguageModelTextPart => part instanceof vscode.LanguageModelTextPart)
    .map((part) => part.value)
    .join('');
}

function showAgentsInPicker(): boolean {
  return vscode.workspace.getConfiguration('realai').get<boolean>('showAgentsInChatModelPicker', true) !== false;
}

function normalizeAgentRows(raw: unknown): Array<{ id: string; name: string }> {
  const out: Array<{ id: string; name: string }> = [];
  const seen = new Set<string>();
  const push = (row: any) => {
    if (row == null) return;
    if (typeof row === 'string') {
      const id = row.trim();
      if (!id || seen.has(id)) return;
      seen.add(id);
      out.push({ id, name: id });
      return;
    }
    if (typeof row !== 'object') return;
    const id = String(row.id || row.agent_id || row.name || row.slug || '').trim();
    if (!id || seen.has(id)) return;
    seen.add(id);
    out.push({ id, name: String(row.name || row.title || row.label || id) });
  };
  if (Array.isArray(raw)) {
    for (const row of raw) push(row);
    return out;
  }
  if (raw && typeof raw === 'object') {
    const obj = raw as Record<string, unknown>;
    for (const key of ['data', 'agents', 'items', 'results']) {
      if (Array.isArray(obj[key])) {
        for (const row of obj[key] as any[]) push(row);
        if (out.length) return out;
      }
    }
  }
  return out;
}

function hiveRoleRows(hive: any): Array<{ id: string; name: string }> {
  const roles = hive?.roles || hive?.core_roles || hive?.agents || hive?.hive_agents || [];
  return normalizeAgentRows(roles);
}


function stripChatWrappers(text: string): string {
  return (text || '')
    .replace(/<environment_info>[\s\S]*?<\/environment_info>/gi, ' ')
    .replace(/<workspace_info>[\s\S]*?<\/workspace_info>/gi, ' ')
    .replace(/<user_info>[\s\S]*?<\/user_info>/gi, ' ')
    .replace(/```[\s\S]*?```/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();
}

/** True when Chat only injected IDE context and left no real user prompt. */
function isWrapperOnlyPrompt(text: string): boolean {
  const raw = (text || '').trim();
  if (!raw) return true;
  const core = stripChatWrappers(raw);
  if (!core) return true;
  // Tiny residue after stripping (punctuation / Continuations) counts as empty.
  if (core.length < 3) return true;
  return false;
}

function detectLocalSlash(text: string): 'phase' | 'patches' | 'repo' | 'help' | null {
  const raw = (text || '').trim();
  if (!raw) return 'phase';
  const core = stripChatWrappers(raw);
  // Cursor/VS Code Chat often sends ONLY environment/workspace XML for slash turns.
  if (!core) return 'phase';
  const hay = (core + '\n' + raw).toLowerCase();
  const slashLine = (core + '\n' + raw)
    .split(/\r?\n/)
    .map((l) => l.trim())
    .find((l) => /^\/(phase|where|patches|audit|repo|read|help)\b/i.test(l));
  const candidate = (slashLine || core).toLowerCase();
  if (
    /(?:^|[\s>`])\/phase\b|(?:^|[\s>`])\/where\b/.test(hay) ||
    /\bwhere are we\b|\bdevelopment status\b|\bwhat phase\b/.test(candidate)
  ) {
    return 'phase';
  }
  if (/(?:^|[\s>`])\/patches\b|(?:^|[\s>`])\/audit\b/.test(hay) || /\bconcrete\s+patches\b/.test(candidate)) {
    return 'patches';
  }
  if (/(?:^|[\s>`])\/repo\b|(?:^|[\s>`])\/read\b/.test(hay)) {
    return 'repo';
  }
  if (/(?:^|[\s>`])\/help\b/.test(hay)) {
    return 'help';
  }
  const stripped = candidate.replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ').trim();
  if (stripped === '/phase' || stripped === '/where' || stripped.startsWith('/phase ')) return 'phase';
  if (stripped === '/patches' || stripped.startsWith('/patches ')) return 'patches';
  if (stripped === '/repo' || stripped.startsWith('/repo ')) return 'repo';
  return null;
}

function formatAgentResult(result: unknown): string {
  if (result == null) return '(empty agent result)';
  if (typeof result === 'string') return result;
  const r: any = result;
  const inner = r?.result && typeof r.result === 'object' ? r.result : r;
  const lines: string[] = [];
  const agentId = r?.agent_id || inner?.agent_id;
  const mode = r?.mode || inner?.mode;
  if (agentId || mode) {
    lines.push(`[RealAI] agent=${agentId || '?'} mode=${mode || '?'}`);
  }
  const worker = inner?.worker || inner?.stage_outputs?.worker;
  const critic = inner?.critic || inner?.stage_outputs?.critic;
  if (typeof worker === 'string' && worker.trim()) {
    // Prefer worker summary section if present
    const m = worker.match(/##\s*Worker summary[\s\S]*/i);
    lines.push(m ? m[0].trim() : worker.trim());
  }
  if (typeof critic === 'string' && critic.trim()) {
    const c = critic.trim();
    lines.push(c.length > 1200 ? c.slice(0, 1200) + '\n...' : c);
  }
  if (lines.length <= 1) {
    let text = JSON.stringify(result, null, 2);
    if (text.length > 4000) text = text.slice(0, 4000) + '\n...(truncated)';
    lines.push(text);
  }
  let out = lines.join('\n\n');
  if (out.length > 6000) out = out.slice(0, 6000) + '\n...(truncated)';
  return out;
}

async function localPhaseReport(client: RealAIClient): Promise<string> {
  const [snap, ctx] = await Promise.all([collectStackSnapshot(client), buildContextSnapshot()]);
  const stage = snap.stage || buildStageBrief();
  const foreign = ctx.hostMode === 'foreign' || !!ctx.foreignRepo;
  return [
    `1) ${stage.phaseId} - ${stage.phaseTitle}`,
    `   tip: ${stage.tipLine}`,
    `2) apps/vscode realai-vscode@${stage.extensionVersion}`,
    `3) Hive ${snap.hiveOk ? 'OK' : 'DOWN'} ${snap.baseUrl} · Vulkan ${snap.vulkanOk ? 'OK' : '?'} · Voice ${snap.voiceOk ? 'OK' : 'off'}`,
    `   tools ${snap.toolsCount} · agents ${snap.agentsCount} · caps ${snap.capabilitiesCount}`,
    `4) host ${ctx.hostMode || 'product'} · workspace ${ctx.workspaceName} · root ${ctx.workspaceRoot}`,
    `   product home ${ctx.productHome || stage.productHome}`,
    foreign
      ? `   FOREIGN REPO: full-stack learn/code/build in this workspace (Hive stays at product home).`
      : `   PRODUCT tree: RealAI-clean / package work.`,
    `5) git ${ctx.gitBranch ? ctx.gitBranch + (ctx.gitDirty ? '*' : '') : 'n/a'}`,
    `6) abilities: ${stage.abilityRollup.slice(0, 6).join(' | ')}`,
    foreign
      ? `7) Next: explore this repo, then ask for concrete patches under its paths - not RealAI health fluff.`
      : `7) Next: /patches for apps/vscode auditor; /repo for workspace_list.`,
  ].join('\n');
}

/** Standalone RealAI Hive provider for VS Code Chat - models + agents, full-stack tools. */
export class RealAILanguageModelChatProvider implements vscode.LanguageModelChatProvider {
  private readonly _onDidChange = new vscode.EventEmitter<void>();
  readonly onDidChangeLanguageModelChatInformation = this._onDidChange.event;

  constructor(private readonly getClient: () => RealAIClient) {}

  /** Call after Hive base URL / model / agent config changes so VS Code re-queries. */
  refresh(): void {
    this._onDidChange.fire();
  }

  private contextTokens(): number {
    const configured = vscode.workspace
      .getConfiguration('realai')
      .get<number>('contextTokens', DEFAULT_CONTEXT_TOKENS);
    return Number.isFinite(configured) && configured >= 1024
      ? Math.floor(configured)
      : DEFAULT_CONTEXT_TOKENS;
  }

  private infoBase(id: string, name: string, family: string) {
    const contextTokens = this.contextTokens();
    return {
      id,
      name,
      family,
      version: '1.0.0',
      maxInputTokens: contextTokens,
      maxOutputTokens: 4096,
      // Chat coder assistant = full stack (Hive tools/abilities)
      capabilities: { imageInput: false, toolCalling: true },
    } as vscode.LanguageModelChatInformation;
  }

  async provideLanguageModelChatInformation(
    _options: vscode.PrepareLanguageModelChatModelOptions,
    _token: vscode.CancellationToken
  ): Promise<vscode.LanguageModelChatInformation[]> {
    const client = this.getClient();
    const entries: vscode.LanguageModelChatInformation[] = [];

    // Dedicated full-stack coder entry under RealAI provider
    entries.push(
      this.infoBase(
        CODER_FULLSTACK_ID,
        'RealAI: coder (full stack)',
        'realai-coder'
      )
    );

    let models: Array<{ id: string }> = [];
    try {
      const res = await client.listModels();
      models = res?.data ?? [];
    } catch {
      models = [];
    }
    for (const m of models) {
      if (!m?.id) continue;
      entries.push(this.infoBase(m.id, `RealAI: ${m.id}`, 'realai'));
    }

    if (showAgentsInPicker()) {
      const agentMap = new Map<string, string>();
      try {
        const agentsRaw = await client.listAgents();
        for (const a of normalizeAgentRows(agentsRaw)) {
          agentMap.set(a.id, a.name);
        }
      } catch {
        /* agents endpoint optional */
      }
      try {
        const hive = await client.getHive();
        for (const a of hiveRoleRows(hive)) {
          if (!agentMap.has(a.id)) agentMap.set(a.id, a.name);
        }
      } catch {
        /* hive optional */
      }
      for (const [id, name] of agentMap) {
        entries.push(
          this.infoBase(`${AGENT_PREFIX}${id}`, `RealAI Agent: ${name}`, 'realai-agent')
        );
      }
    }

    // If Hive is down entirely, still surface the coder fullstack entry so provider is not empty.
    return entries;
  }

  async provideLanguageModelChatResponse(
    model: vscode.LanguageModelChatInformation,
    messages: readonly vscode.LanguageModelChatRequestMessage[],
    _options: vscode.ProvideLanguageModelChatResponseOptions,
    progress: vscode.Progress<vscode.LanguageModelResponsePart>,
    token: vscode.CancellationToken
  ): Promise<void> {
    const client = this.getClient();
    const cfg = vscode.workspace.getConfiguration('realai');
    const configuredModel =
      cfg.get<string>('model') ||
      client.selectedModel ||
      'realai-hive';

    let agentId = '';
    let inferenceModel = configuredModel;
    const isCoderFullstack = model.id === CODER_FULLSTACK_ID;
    const isAgentPick = model.id.startsWith(AGENT_PREFIX);

    if (isCoderFullstack) {
      agentId = (cfg.get<string>('agentId') || '').trim() || 'coder';
      inferenceModel = configuredModel;
    } else if (isAgentPick) {
      agentId = model.id.slice(AGENT_PREFIX.length).trim();
      inferenceModel = configuredModel;
    } else {
      // Selected a Hive model entry - use it for inference; keep any configured default agent
      inferenceModel = model.id || configuredModel;
      agentId = (client.defaultAgentId || '').trim();
    }

    client.setModel(inferenceModel);

    const chatMessages: ChatMessage[] = messages.map((m) => ({
      role: toRealAIRole(m.role),
      content: extractText(m.content),
    }));

    const contextTokens = this.contextTokens();
    const fittedMessages = fitMessagesToContext(chatMessages, contextTokens);

    const lastUser =
      [...fittedMessages].reverse().find((m) => m.role === 'user') ||
      [...chatMessages].reverse().find((m) => m.role === 'user');
    const rawTask = (lastUser?.content || '').trim() || '';
    // Strip IDE XML wrappers before slash detect / Hive dispatch (Cursor often sends wrappers only).
    const coreTask = stripChatWrappers(rawTask);
    const task = coreTask || rawTask || 'Continue';

    // Deterministic Console slash intents - never hive-dispatch these (/phase in foreign repos).
    // Wrapper-only prompts (no real user text) => local /phase, not health-fluff multi.
    let localIntent = detectLocalSlash(rawTask) || detectLocalSlash(coreTask);
    if (!localIntent && isWrapperOnlyPrompt(rawTask) && (isCoderFullstack || isAgentPick)) {
      localIntent = 'phase';
    }
    if (localIntent) {
      let text = '';
      try {
        if (localIntent === 'phase') {
          text = await localPhaseReport(client);
        } else if (localIntent === 'patches') {
          text = auditAppsVscode().report;
        } else if (localIntent === 'repo') {
          try {
            const listing = await client.executeTool('workspace_list', { path: '.' });
            const entries = listing?.result?.entries || [];
            const wsRoot = listing?.result?.workspace || '';
            const lines = (entries as any[])
              .slice(0, 80)
              .map((e: any) => `- ${e.type === 'dir' ? 'dir ' : 'file'} ${e.name}`);
            text = `Hive workspace_list for ${wsRoot}:\n` + lines.join('\n');
          } catch (e: any) {
            const ctx = await buildContextSnapshot();
            text =
              `Hive workspace_list failed (${e?.message || e}).\n` +
              `Local IDE sketch of ${ctx.workspaceRoot}:\n` +
              (ctx.treeSketch || []).slice(0, 40).map((x) => `- ${x}`).join('\n');
          }
        } else {
          text = [
            'RealAI Chat slash help:',
            '- /phase or /where - stage + host mode (foreign vs product) + stack',
            '- /patches - deterministic apps/vscode auditor',
            '- /repo - workspace listing',
            '- Otherwise coder/agent picks dispatch Hive; tools stay on for full-stack chat.',
          ].join('\n');
        }
      } catch (e: any) {
        text = `Local slash failed: ${e?.message || e}`;
      }
      progress.report(new vscode.LanguageModelTextPart(text));
      return;
    }

    // Setting controls coder/agent Chat picks only (default on) - plain model ids stay stream-only.
    const chatDispatchAgents = cfg.get<boolean>('chatDispatchAgents', true) !== false;
    const shouldDispatch = chatDispatchAgents && (isCoderFullstack || isAgentPick);

    let agentRunSummary = '';
    if (shouldDispatch) {
      const dispatchId = agentId || 'coder';
      progress.report(
        new vscode.LanguageModelTextPart(`[RealAI] Dispatching Hive agent ${dispatchId}...\n`)
      );
      try {
        // Always send cleaned user text - never the raw environment/workspace XML blob.
        const hiveTask = coreTask || task;
        const result = await client.runAgent(dispatchId, hiveTask, { multi: true }); // hive/multi lights Agents UI
        const text = formatAgentResult(result);
        progress.report(new vscode.LanguageModelTextPart(text + '\n'));
        agentRunSummary = text.slice(0, 800);
        // Multi already produced the answer; skip streamChat so Chat is not empty after a huge JSON dump.
        return;
      } catch (e) {
        const err = e instanceof Error ? e.message : String(e);
        progress.report(
          new vscode.LanguageModelTextPart(
            `[RealAI] Agent dispatch failed: ${err}\nFalling back to chat stream...\n\n`
          )
        );
      }
    }

    let messagesForStream = fittedMessages;
    // Prefer cleaned user content for the model prompt.
    if (coreTask && lastUser) {
      messagesForStream = fittedMessages.map((m, idx) => {
        const isLastUser =
          m.role === 'user' &&
          idx === fittedMessages.length - 1 - [...fittedMessages].reverse().findIndex((x) => x.role === 'user');
        return isLastUser ? { ...m, content: coreTask } : m;
      });
    }

    // Full-stack Chat coder assistant posture (match browser /console): tools + memory on.
    const streamOpts = {
      tools: true,
      memory: true,
      agentId: agentId || undefined,
      temperature: 0.35,
      maxTokens: 2048,
      multiAgent: false as boolean,
    };

    await new Promise<void>((resolve, reject) => {
      const cancelListener = token.onCancellationRequested(() => {
        cancelListener.dispose();
        resolve();
      });
      client
        .streamChat(
          messagesForStream,
          {
            onToken: (text) => progress.report(new vscode.LanguageModelTextPart(text)),
            onDone: () => {
              cancelListener.dispose();
              resolve();
            },
            onError: (error) => {
              cancelListener.dispose();
              reject(new Error(error));
            },
          },
          streamOpts
        )
        .catch((err) => {
          cancelListener.dispose();
          reject(err);
        });
    });
  }

  async provideTokenCount(
    _model: vscode.LanguageModelChatInformation,
    text: string | vscode.LanguageModelChatRequestMessage,
    _token: vscode.CancellationToken
  ): Promise<number> {
    const str = typeof text === 'string' ? text : extractText(text.content);
    return Math.ceil(str.length / 4);
  }
}
