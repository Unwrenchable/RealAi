import * as fs from 'fs';
import * as path from 'path';
import * as vscode from 'vscode';
import { RealAIClient, ChatMessage, StreamCallbacks } from './realaiClient';
import { buildContextSnapshot, ContextSnapshot } from './contextPack';
import { detectWorkspaceMode } from './workspaceMode';
import { collectStackSnapshot } from './stackStatus';
import { buildStageBrief } from './stageContext';
import { auditAppsVscode } from './extensionAudit';

const PANEL_UI_VERSION = '1.0.2';

export class RealAIChatPanel {
  public static currentPanel: RealAIChatPanel | undefined;

  public static get instance(): RealAIChatPanel | undefined {
    return RealAIChatPanel.currentPanel;
  }

  private readonly panel: vscode.WebviewPanel;
  private readonly client: RealAIClient;
  private readonly ctx: vscode.ExtensionContext;
  private readonly uiVersion = PANEL_UI_VERSION;

  /** User/assistant turns only (system rebuilt each request) */
  private messages: ChatMessage[] = [];
  private isStreaming = false;
  private latestContext?: ContextSnapshot;

  private _lastResponse = '';
  public get lastResponse(): string {
    return this._lastResponse;
  }

  private pendingInput = '';

  static createOrShow(ctx: vscode.ExtensionContext, client: RealAIClient) {
    if (RealAIChatPanel.currentPanel) {
      // Force HTML refresh so upgrades never keep a stale webview.
      RealAIChatPanel.currentPanel.rebindHtml();
      RealAIChatPanel.currentPanel.panel.reveal(vscode.ViewColumn.Beside);
      void RealAIChatPanel.currentPanel.refreshContext(true);
      return;
    }

    const webviewRoot = vscode.Uri.file(path.join(ctx.extensionPath, 'webview'));
    const panel = vscode.window.createWebviewPanel(
      'realaiChat',
      `RealAI Dev Chat v${PANEL_UI_VERSION}`,
      vscode.ViewColumn.Beside,
      {
        enableScripts: true,
        retainContextWhenHidden: true,
        localResourceRoots: [webviewRoot],
      }
    );
    RealAIChatPanel.currentPanel = new RealAIChatPanel(panel, client, ctx);
  }

  constructor(panel: vscode.WebviewPanel, client: RealAIClient, ctx: vscode.ExtensionContext) {
    this.panel = panel;
    this.client = client;
    this.ctx = ctx;
    this.rebindHtml();

    this.panel.onDidDispose(() => {
      RealAIChatPanel.currentPanel = undefined;
    });

    this.panel.webview.onDidReceiveMessage(async (msg) => {
      switch (msg.command) {
        case 'chat':
          await this.handleUserText(msg.text);
          break;
        case 'stream':
          await this.handleUserText(msg.text);
          break;
        case 'clear':
          this.clear();
          break;
        case 'refreshContext':
          await this.refreshContext(true);
          break;
        case 'ready':
          await this.refreshContext(true);
          this.panel.webview.postMessage({
            command: 'version',
            version: this.uiVersion,
          });
          if (this.pendingInput) {
            const text = this.pendingInput;
            this.pendingInput = '';
            this.panel.webview.postMessage({ command: 'setInput', text });
          }
          break;
        case 'insertResponse':
          vscode.commands.executeCommand('realai.insertResponse');
          break;
        case 'openFile':
          if (msg.path) {
            const uri = vscode.Uri.file(msg.path);
            vscode.window.showTextDocument(uri);
          }
          break;
      }
    });

    const sub = vscode.window.onDidChangeActiveTextEditor(() => {
      void this.refreshContext();
    });
    this.panel.onDidDispose(() => sub.dispose());
  }

  public rebindHtml() {
    this.panel.title = `RealAI Dev Chat v${this.uiVersion}`;
    this.panel.webview.html = this.getHtml();
  }

  public setInput(text: string) {
    this.panel.webview.postMessage({ command: 'setInput', text });
  }

  public clear() {
    this.messages = [];
    this._lastResponse = '';
    this.panel.webview.postMessage({ command: 'clear' });
    void this.refreshContext(true);
  }

  public async sendMessage(text: string) {
    await this.handleUserText(text);
  }

  public async refreshContext(announce = false) {
    try {
      this.latestContext = await buildContextSnapshot();
      this.panel.webview.postMessage({
        command: 'context',
        summary: this.latestContext.summaryLine,
        workspace: this.latestContext.workspaceName,
        file: this.latestContext.activeFile || '',
        branch: this.latestContext.gitBranch || '',
        dirty: !!this.latestContext.gitDirty,
        version: this.uiVersion,
      });
      if (announce) {
        this.panel.webview.postMessage({
          command: 'activity',
          text: `Context: ${this.latestContext.summaryLine}`,
        });
      }
    } catch (e: any) {
      this.panel.webview.postMessage({
        command: 'context',
        summary: `context error: ${e?.message || e}`,
        workspace: '',
        file: '',
        branch: '',
        dirty: false,
        version: this.uiVersion,
      });
    }
  }

  /** Show a local (non-LLM) assistant note in the transcript */
  public postLocalAssistant(content: string) {
    this.messages.push({ role: 'assistant', content });
    this._lastResponse = content;
    this.appendMessage('assistant', content);
  }

  public async readRepoSnapshot() {
    this.appendMessage('user', 'Read repo snapshot');
    this.messages.push({ role: 'user', content: 'Read repo snapshot' });

    let listingText = '';
    try {
      const listing = await this.client.executeTool('workspace_list', { path: '.' });
      const entries = listing?.result?.entries || listing?.entries || [];
      const root = listing?.result?.workspace || listing?.workspace || '(hive workspace)';
      const lines = (Array.isArray(entries) ? entries : [])
        .slice(0, 80)
        .map((e: any) => `- ${e.type === 'dir' ? 'dir ' : 'file'} ${e.name}`);
      listingText =
        `Hive workspace_list for ${root}:\n` +
        (lines.length ? lines.join('\n') : JSON.stringify(listing, null, 2));
    } catch (e: any) {
      // Local fallback from IDE context pack
      const snap = await buildContextSnapshot();
      listingText =
        `Hive workspace_list failed (${e?.message || e}).\n` +
        `Local IDE sketch of ${snap.workspaceRoot}:\n` +
        snap.treeSketch.map((t) => `- ${t}`).join('\n');
    }

    // Always show the real listing first — do not ask the model for permission to read.
    this.postLocalAssistant(listingText);

    await this.handleStream(
      [
        'Using the repo snapshot above plus WORKSPACE CONTEXT, answer:',
        '1) What is this repo focused on right now?',
        '2) What is the state of apps/vscode (RealAI extension)?',
        '3) Top 3 concrete finish-next items with paths.',
        'Do not say you cannot read files. Do not give generic product-speak.',
      ].join('\n'),
      { skipUserEcho: true }
    );
  }

  private detectIntent(
    text: string
  ):
    | 'readRepo'
    | 'where'
    | 'next'
    | 'phase'
    | 'tools'
    | 'agents'
    | 'heal'
    | 'caps'
    | 'multi'
    | 'patches'
    | 'help'
    | 'chat' {
    const t = text.toLowerCase().trim();
    if (t === '/help' || t === 'help' || t.startsWith('/help ')) return 'help';
    if (t === '/repo' || t === '/read' || /read\s+repo|repo\s+snapshot|workspace_list/.test(t)) return 'readRepo';
    if (t === '/phase' || t === '/where' || /where are we|development\s+status|orient/.test(t)) return 'where';
    if (
      t === '/patches' ||
      t === '/audit' ||
      /concrete\s+patches/.test(t) ||
      (/apps\/vscode/.test(t) && /patch|audit|harden|fix/.test(t)) ||
      (/list\s+3/.test(t) && /patch/.test(t))
    ) {
      return 'patches';
    }
    if (t === '/tools') return 'tools';
    if (t === '/agents') return 'agents';
    if (t === '/heal' || t === '/self-heal') return 'heal';
    if (t === '/caps' || t === '/capabilities') return 'caps';
    if (t.startsWith('/multi') || t.startsWith('/agent ')) return 'multi';
    if (/what should we finish|finish next|next on the .*extension/.test(t)) return 'next';
    return 'chat';
  }

  private async dumpJsonAsAssistant(title: string, data: unknown) {
    const body = typeof data === 'string' ? data : JSON.stringify(data, null, 2);
    this.postLocalAssistant(`${title}\n\n\`\`\`json\n${body.slice(0, 12000)}\n\`\`\``);
  }

  /** Deterministic Phase I status — does not depend on GGUF / live_exec. */
  private async postPhaseReport() {
    try {
      const [snap, ctx] = await Promise.all([
        collectStackSnapshot(this.client),
        buildContextSnapshot(),
      ]);
      const stage = snap.stage || buildStageBrief();
      const lines = [
        `1) Current phase + tip`,
        `   ${stage.phaseId} — ${stage.phaseTitle}`,
        `   tip: ${stage.tipLine}`,
        ``,
        `2) Extension status`,
        `   apps/vscode realai-vscode@${stage.extensionVersion} (Ultimate Hub + Chat ui v${this.uiVersion})`,
        `   sources: extension.ts, hubView.ts, chatPanel.ts, contextPack.ts, stageContext.ts, stackStatus.ts, realaiClient.ts`,
        ``,
        `3) Runtime posture`,
        `   Hive ${snap.hiveOk ? 'OK' : 'DOWN'} ${snap.baseUrl} (${snap.service || 'n/a'})`,
        `   Vulkan ${snap.vulkanOk ? 'OK' : '?'} · Voice ${snap.voiceOk ? 'OK' : 'off'} (${snap.voiceUrl})`,
        `   tools ${snap.toolsCount} · agents ${snap.agentsCount} · caps ${snap.capabilitiesCount} · hive roles ${snap.hiveAgentCount}`,
        `   self-heal ${snap.selfHealEnabled ? 'on' : 'off'} · promote_actionable ${snap.promoteActionable ?? 'n/a'} · lora ${snap.loraCount ?? 'n/a'}`,
        ``,
        `4) Git posture`,
        ctx.gitBranch
          ? `   branch ${ctx.gitBranch}${ctx.gitDirty ? ' (dirty)' : ' (clean)'}`
          : `   n/a (no git metadata for this workspace folder)`,
        ``,
        `5) Top rolled-up abilities`,
        ...stage.abilityRollup.slice(0, 8).map((a) => `   • ${a}`),
        ``,
        `6) Next 3 concrete steps`,
        `   1. Keep Hive healthy: realai-stack / realai-health (expect :8001 + :8080)`,
        `   2. Harden apps/vscode chat grounding: prefer /phase /repo /multi over free prose when auditing`,
        `   3. Optional Voice Lab :8890 — start realai voice service if you want Hub Voice OK`,
      ];
      this.postLocalAssistant(lines.join('\n'));
      await this.refreshContext();
    } catch (e: any) {
      this.postLocalAssistant(`Phase report failed: ${e?.message || e}`);
    }
  }

  private looksLikeGenericVscodeAdvice(text: string): boolean {
    const t = (text || '').toLowerCase();
    return (
      t.includes('live share') ||
      t.includes('debug adapter support') ||
      t.includes('update to the latest version of vscode') ||
      t.includes('marketplace') ||
      (t.includes('install the') && t.includes('extension'))
    );
  }

  private async runGroundedMulti(task: string) {
    const stage = buildStageBrief();
    const root =
      vscode.workspace.workspaceFolders?.[0]?.uri.fsPath || stage.productHome;
    const extFiles = [
      'apps/vscode/package.json',
      'apps/vscode/src/extension.ts',
      'apps/vscode/src/chatPanel.ts',
      'apps/vscode/src/hubView.ts',
      'apps/vscode/src/realaiClient.ts',
      'apps/vscode/src/contextPack.ts',
      'apps/vscode/webview/hub.html',
      'apps/vscode/webview/index.html',
    ].filter((p) => fs.existsSync(path.join(root, p)));

    const mode = detectWorkspaceMode(root);
    const grounded = [
      mode.hostMode === 'foreign'
        ? `Host mode: FOREIGN REPO. Workspace ${mode.workspaceName} at ${mode.workspaceRoot}. Product home ${mode.productHome}.`
        : `Product: RealAI Ultimate VS Code extension (realai-vscode@${stage.extensionVersion}) at ${stage.productHome}.`,
      `Workspace root: ${root}`,
      `Hive: http://127.0.0.1:8001`,
      mode.hostMode === 'foreign'
        ? `Build hints: ${mode.stack.buildHints.join(', ')}`
        : `Relevant paths only: ${extFiles.join(', ')}`,
      `Task: ${task}`,
      mode.hostMode === 'foreign'
        ? `Rules: Full-stack in THIS repo. Propose concrete patches with exact paths under the host workspace.`
        : `Rules: Propose 3 concrete patches with exact paths under apps/vscode/.`,
      `Forbidden: Live Share, marketplace installs, "update VS Code", Apache Hive/Hadoop jokes, generic IDE tips.`,
    ].join('\n');

    try {
      const result = await this.client.multiAgentRun(grounded);
      const blob = JSON.stringify(result?.final_output || result || {});
      if (this.looksLikeGenericVscodeAdvice(blob)) {
        this.postLocalAssistant(
          [
            'Multi-agent returned generic VS Code marketplace advice — discarding as ungrounded.',
            '',
            'Local concrete patch candidates for apps/vscode:',
            '1. apps/vscode/src/chatPanel.ts — keep /phase as deterministic stack report (done in 1.0.1); extend /multi discard rules.',
            '2. apps/vscode/src/realaiClient.ts — send X-RealAI-Tools: off on IDE chat so Hive live_exec does not intercept prose.',
            '3. apps/vscode/src/hubView.ts / webview/hub.html — surface phase report + multi-agent grounded audit buttons.',
            '',
            'Raw multi-agent payload kept below for debugging:',
          ].join('\n')
        );
        await this.dumpJsonAsAssistant('Multi-agent raw (ungrounded)', result);
        return;
      }
      await this.dumpJsonAsAssistant('Multi-agent result', result);
      // Short grounded follow-up without trigger words like git/command/run
      await this.handleStream(
        [
          'Using only apps/vscode paths, rewrite the multi-agent result into 3 concrete file patches.',
          'Each patch: path + what to change + why.',
          'No marketplace tips.',
          '',
          String(result?.final_output || '').slice(0, 6000),
        ].join('\n'),
        { skipUserEcho: true }
      );
    } catch (e: any) {
      this.postLocalAssistant(`Multi-agent failed: ${e?.message || e}`);
      await this.handleStream(
        `Propose 3 concrete patches under apps/vscode for: ${task}. Paths only under apps/vscode. No marketplace tips.`,
        { skipUserEcho: true }
      );
    }
  }

  private async handleUserText(text: string) {
    const trimmed = (text || '').trim();
    if (!trimmed) return;

    const intent = this.detectIntent(trimmed);
    if (intent === 'help') {
      this.appendMessage('user', trimmed);
      this.messages.push({ role: 'user', content: trimmed });
      this.postLocalAssistant(
        [
          'RealAI Ultimate slash commands:',
          '- /phase or /where — development stage + stack posture',
          '- /repo — Hive/local workspace listing + summary',
          '- /patches — 3 concrete apps/vscode patches (deterministic)',
          '- /tools — list Hive tools',
          '- /agents — list agents / hive roles',
          '- /heal — self-heal status',
          '- /caps — capabilities',
          '- /multi <task> — multi-agent pipeline (grounded)',
          '- /help — this list',
          '',
          'Or use the RealAI activity-bar Hub for one-click actions.',
        ].join('\n')
      );
      return;
    }
    if (intent === 'readRepo') {
      await this.readRepoSnapshot();
      return;
    }
    if (intent === 'patches') {
      this.appendMessage('user', trimmed);
      this.messages.push({ role: 'user', content: trimmed });
      this.postLocalAssistant(auditAppsVscode().report);
      return;
    }
    if (intent === 'tools') {
      this.appendMessage('user', trimmed);
      this.messages.push({ role: 'user', content: trimmed });
      try {
        const tools = await this.client.listTools();
        const names = (tools.tools || [])
          .map((t: any) => t?.function?.name || t?.name)
          .filter(Boolean);
        this.postLocalAssistant(
          `Hive tools (${names.length}):\n` + names.slice(0, 120).map((n: string) => `- ${n}`).join('\n')
        );
      } catch (e: any) {
        this.postLocalAssistant(`List tools failed: ${e?.message || e}`);
      }
      return;
    }
    if (intent === 'agents') {
      this.appendMessage('user', trimmed);
      this.messages.push({ role: 'user', content: trimmed });
      try {
        const [hive, agents] = await Promise.all([this.client.getHive(), this.client.listAgents()]);
        const present = hive?.agents?.present || [];
        const ids = (agents?.data || []).map((a: any) => a.id).slice(0, 80);
        this.postLocalAssistant(
          `Hive core roles (${present.length}): ${present.join(', ')}\n\nAgent catalog sample (${ids.length}):\n` +
            ids.map((id: string) => `- ${id}`).join('\n')
        );
      } catch (e: any) {
        this.postLocalAssistant(`List agents failed: ${e?.message || e}`);
      }
      return;
    }
    if (intent === 'heal') {
      this.appendMessage('user', trimmed);
      this.messages.push({ role: 'user', content: trimmed });
      try {
        await this.dumpJsonAsAssistant('Self-heal status', await this.client.getSelfHealStatus());
      } catch (e: any) {
        this.postLocalAssistant(`Self-heal failed: ${e?.message || e}`);
      }
      return;
    }
    if (intent === 'caps') {
      this.appendMessage('user', trimmed);
      this.messages.push({ role: 'user', content: trimmed });
      try {
        const caps = await this.client.getCapabilities();
        const list = caps?.capabilities || caps;
        const names = Array.isArray(list)
          ? list.map((c: any) => (typeof c === 'string' ? c : c.id || JSON.stringify(c)))
          : [];
        this.postLocalAssistant(
          `Capabilities (${names.length}):\n` + names.slice(0, 100).map((n: string) => `- ${n}`).join('\n')
        );
      } catch (e: any) {
        this.postLocalAssistant(`Capabilities failed: ${e?.message || e}`);
      }
      return;
    }
    if (intent === 'multi') {
      const task = trimmed.replace(/^\/multi\s*/i, '').replace(/^\/agent\s*/i, '').trim();
      if (!task) {
        this.postLocalAssistant('Usage: /multi <task to orchestrate>');
        return;
      }
      this.appendMessage('user', trimmed);
      this.messages.push({ role: 'user', content: trimmed });
      await this.runGroundedMulti(task);
      return;
    }
    if (intent === 'where' || intent === 'phase') {
      this.appendMessage('user', trimmed.startsWith('/') ? trimmed : 'Where are we?');
      this.messages.push({ role: 'user', content: trimmed });
      await this.postPhaseReport();
      return;
    }
    if (intent === 'next') {
      await this.handleStream(
        [
          trimmed,
          '',
          'Constraints: use REALAI STAGE + WORKSPACE CONTEXT. Prefer apps/vscode + Hive surfaces.',
          'Give 3 concrete finish-next items with file paths. No marketplace fluff.',
        ].join('\n')
      );
      return;
    }

    await this.handleStream(trimmed);
  }

  private async composeMessages(userText: string): Promise<ChatMessage[]> {
    this.latestContext = await buildContextSnapshot();
    this.panel.webview.postMessage({
      command: 'context',
      summary: this.latestContext.summaryLine,
      workspace: this.latestContext.workspaceName,
      file: this.latestContext.activeFile || '',
      branch: this.latestContext.gitBranch || '',
      dirty: !!this.latestContext.gitDirty,
      version: this.uiVersion,
    });

    const groundedUser = `${this.latestContext.userContextBlock}\n\nUSER REQUEST:\n${userText}`;

    return [
      { role: 'system', content: this.latestContext.systemPrompt },
      ...this.messages.slice(0, -1).slice(-10),
      { role: 'user', content: groundedUser },
    ];
  }

  private async handleStream(
    text: string,
    opts: { skipUserEcho?: boolean; multiAgent?: boolean } = {}
  ) {
    if (this.isStreaming) {
      return;
    }
    this.isStreaming = true;

    if (!opts.skipUserEcho) {
      this.messages.push({ role: 'user', content: text });
      this.appendMessage('user', text);
    } else {
      this.messages.push({ role: 'user', content: text });
    }

    this.panel.webview.postMessage({ command: 'streamStart' });

    let fullContent = '';

    try {
      const messages = await this.composeMessages(text);

      const callbacks: StreamCallbacks = {
        onToken: (token: string) => {
          if (typeof token !== 'string' || !token) return;
          fullContent += token;
          this.panel.webview.postMessage({ command: 'streamToken', token });
        },
        onDone: (_fullContent: string) => {
          this.isStreaming = false;
          const cleaned = fullContent.replace(/\n{3,}/g, '\n\n').trim();
          this.messages.push({ role: 'assistant', content: cleaned || fullContent });
          this._lastResponse = cleaned || fullContent;
          this.panel.webview.postMessage({
            command: 'streamEnd',
            content: cleaned || fullContent,
          });
        },
        onError: (error: string) => {
          this.isStreaming = false;
          this.appendMessage('error', `Error: ${error}`);
          this.panel.webview.postMessage({ command: 'streamEnd', content: '' });
        },
      };

      await this.client.streamChat(messages, callbacks, {
        multiAgent: !!opts.multiAgent,
      });

      // Empty stream / operator short-circuit → non-stream fallback.
      if (!fullContent.trim()) {
        this.isStreaming = false;
        this.panel.webview.postMessage({ command: 'streamEnd', content: '' });
        try {
          const reply = (await this.client.chat(messages, {
            multiAgent: !!opts.multiAgent,
          })).trim();
          if (reply) {
            // Drop empty assistant placeholder if streamEnd created nothing useful
            this.messages.push({ role: 'assistant', content: reply });
            this._lastResponse = reply;
            this.appendMessage('assistant', reply);
          } else {
            this.appendMessage(
              'error',
              'Empty model response. Use /phase for a deterministic status report.'
            );
          }
        } catch (fallbackErr: any) {
          this.appendMessage('error', `Error: ${fallbackErr?.message || fallbackErr}`);
        }
      }
    } catch (e: any) {
      this.isStreaming = false;
      this.appendMessage('error', `Error: ${e?.message || e}`);
      this.panel.webview.postMessage({ command: 'streamEnd', content: '' });
    }
  }

  private appendMessage(role: string, content: string) {
    this.panel.webview.postMessage({ command: 'append', role, content });
  }

  static postActivity(text: string) {
    RealAIChatPanel.currentPanel?.panel.webview.postMessage({
      command: 'activity',
      text,
    });
  }

  private getHtml(): string {
    const htmlPath = path.join(this.ctx.extensionPath, 'webview', 'index.html');
    try {
      const raw = fs.readFileSync(htmlPath, 'utf8');
      // Cache-bust comment so VS Code cannot reuse a stale document body.
      return raw.replace(
        '</head>',
        `<!-- realai-ui ${this.uiVersion} ${Date.now()} -->\n</head>`
      );
    } catch (e: any) {
      return `<!DOCTYPE html><html><body style="font-family:sans-serif;padding:16px;background:#0d0d1a;color:#e0e0ff">
        <h2>RealAI Chat v${this.uiVersion}</h2>
        <p>Failed to load webview/index.html</p>
        <pre>${String(e?.message || e)}</pre>
      </body></html>`;
    }
  }
}
