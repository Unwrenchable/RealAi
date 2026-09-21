import * as fs from 'fs';
import * as path from 'path';
import * as vscode from 'vscode';
import { RealAIClient, ChatMessage } from './realaiClient';
import { collectStackSnapshot } from './stackStatus';
import { buildStageBrief } from './stageContext';
import { auditAppsVscode } from './extensionAudit';
import { buildContextSnapshot } from './contextPack';
import { detectWorkspaceMode } from './workspaceMode';

const UI_VERSION = require('../package.json').version as string;

type ThreadMsg = { role: 'user' | 'assistant' | 'system'; content: string };

export class RealAIConsolePanel {
  public static current: RealAIConsolePanel | undefined;
  private panel: vscode.WebviewPanel;
  private client: RealAIClient;
  private ctx: vscode.ExtensionContext;
  private lastResponse = '';
  private refreshTimer: ReturnType<typeof setInterval> | undefined;

  static createOrShow(ctx: vscode.ExtensionContext, client: RealAIClient) {
    if (RealAIConsolePanel.current) {
      // Keep webview state (threads). Only refresh bootstrap data.
      RealAIConsolePanel.current.client = client;
      RealAIConsolePanel.current.panel.reveal(vscode.ViewColumn.Active);
      void RealAIConsolePanel.current.pushBootstrap();
      return RealAIConsolePanel.current;
    }
    const panel = vscode.window.createWebviewPanel(
      'realaiConsole',
      `RealAI Console v${UI_VERSION}`,
      vscode.ViewColumn.Active,
      {
        enableScripts: true,
        retainContextWhenHidden: true,
        localResourceRoots: [
          vscode.Uri.file(path.join(ctx.extensionPath, 'webview')),
          vscode.Uri.file(path.join(ctx.extensionPath, 'media')),
          ...((vscode.workspace.workspaceFolders || []).map((f) => f.uri)),
        ],
      }
    );
    RealAIConsolePanel.current = new RealAIConsolePanel(panel, client, ctx);
    return RealAIConsolePanel.current;
  }

  private constructor(
    panel: vscode.WebviewPanel,
    client: RealAIClient,
    ctx: vscode.ExtensionContext
  ) {
    this.panel = panel;
    this.client = client;
    this.ctx = ctx;
    this.rebind();
    panel.onDidDispose(() => {
      if (this.refreshTimer) {
        clearInterval(this.refreshTimer);
        this.refreshTimer = undefined;
      }
      if (RealAIConsolePanel.current === this) {
        RealAIConsolePanel.current = undefined;
      }
    });
    panel.onDidChangeViewState((e) => {
      if (e.webviewPanel.visible && RealAIConsolePanel.current === this) {
        void this.pushBootstrap();
      }
    });
    this.refreshTimer = setInterval(() => {
      if (RealAIConsolePanel.current === this) {
        void this.pushBootstrap();
      }
    }, 45000);
    panel.webview.onDidReceiveMessage(async (msg) => {
      try {
        if (msg?.command === 'openBrowserConsole') {
          const base = this.client.getBaseUrl().replace(/\/$/, '');
          await vscode.env.openExternal(vscode.Uri.parse(`${base}/console`));
          return;
        }
        if (msg?.command === 'setVoice') {
          this.client.voiceEnabled = !!msg.on;
          return;
        }
        await this.onMessage(msg);
      } catch (e: any) {
        this.post({ command: 'error', text: String(e?.message || e) });
      }
    });
    void this.pushBootstrap();
  }

  /** Public refresh used by realai.refreshAbilities / config changes */
  public async refreshBootstrap() {
    await this.pushBootstrap();
  }
  get lastAssistant(): string {
    return this.lastResponse;
  }

  /** Public entry used by extension commands / Hub buttons */
  async runLocal(kind: 'phase' | 'patches' | 'repo' | string) {
    await this.handleLocal(kind);
  }

  async runChat(text: string) {
    await this.handleChat(text, []);
  }

  private rebind() {
    this.panel.title = `RealAI Console v${UI_VERSION}`;
    this.panel.webview.html = this.html();
  }

  private post(payload: Record<string, unknown>) {
    void this.panel.webview.postMessage(payload);
  }

  private resolveConsoleHtmlPath(): string {
    const workspaceRoots = (vscode.workspace.workspaceFolders || []).map((f) => f.uri.fsPath);
    const extRoot = this.ctx.extensionPath;

    const looksLikeHtml = (filePath: string): boolean => {
      try {
        const head = fs.readFileSync(filePath, { encoding: 'utf8' }).slice(0, 512);
        const trimmed = head.trimStart();
        return (
          trimmed.startsWith('<!DOCTYPE') ||
          trimmed.startsWith('<!doctype') ||
          /<html[\s>]/i.test(head)
        );
      } catch {
        return false;
      }
    };

    const tryFile = (filePath: string, requireHtml: boolean): string | null => {
      try {
        if (!fs.existsSync(filePath) || !fs.statSync(filePath).isFile()) {
          return null;
        }
        if (requireHtml && !looksLikeHtml(filePath)) {
          return null;
        }
        return path.resolve(filePath);
      } catch {
        return null;
      }
    };

    // Prefer packaged + tree webview UI over a workspace console.html Craft dump.
    const ordered: Array<{ path: string; requireHtml: boolean }> = [];
    ordered.push({ path: path.join(extRoot, 'webview', 'console.html'), requireHtml: false });
    for (const root of workspaceRoots) {
      ordered.push({
        path: path.join(root, 'apps', 'vscode', 'webview', 'console.html'),
        requireHtml: false,
      });
    }
    for (const root of workspaceRoots) {
      ordered.push({ path: path.join(root, 'console.html'), requireHtml: true });
    }
    // Legacy install layout (extension nested under product) — HTML-gated.
    ordered.push({ path: path.join(extRoot, '..', '..', 'console.html'), requireHtml: true });

    for (const item of ordered) {
      const hit = tryFile(item.path, item.requireHtml);
      if (hit) {
        return hit;
      }
    }
    return path.join(extRoot, 'webview', 'console.html');
  }

  private html(): string {
    const p = this.resolveConsoleHtmlPath();
    try {
      const cssUri = this.panel.webview.asWebviewUri(
        vscode.Uri.file(path.join(this.ctx.extensionPath, 'webview', 'console.css'))
      );
      const hive = this.client.getBaseUrl().replace(/\/$/, '');
      const csp = [
        `default-src 'none'`,
        `style-src ${this.panel.webview.cspSource} 'unsafe-inline'`,
        `script-src 'unsafe-inline'`,
        `img-src ${this.panel.webview.cspSource} https: data:`,
        `font-src ${this.panel.webview.cspSource} data:`,
        `media-src data: blob:`,
        `connect-src ${hive} http://127.0.0.1:* http://localhost:*`,
      ].join('; ');
      return fs
        .readFileSync(p, 'utf8')
        .replace(/__CONSOLE_CSS__/g, String(cssUri))
        .replace(
          '</head>',
          `<meta http-equiv="Content-Security-Policy" content="${csp}" />
<script>window.__REALAI_HIVE__=${JSON.stringify(hive)};window.__REALAI_CONSOLE_MODE__='vscode';</script>
<!-- console ${UI_VERSION} ${Date.now()} --></head>`
        );
    } catch (e: any) {
      return `<html><body style="background:#07070b;color:#fff;padding:16px;font-family:sans-serif">
        Failed to load console.html: ${String(e?.message || e)}</body></html>`;
    }
  }

  private async pushBootstrap() {
    const [snap, caps, tools, agents, coverage, liveAbilities] = await Promise.all([
      collectStackSnapshot(this.client),
      this.client.getCapabilities().catch((e) => ({ error: String(e) })),
      this.client.listTools().catch((e) => ({ error: String(e), tools: [] })),
      this.client.listAgents().catch((e) => ({ error: String(e), data: [] })),
      this.client.executeTool('ability_coverage', {}).catch(() => null),
      this.client.listAbilities().catch((e) => ({
        abilities: [] as Array<{ id: string; name?: string; status?: string }>,
        source: `error:${String((e as any)?.message || e)}`,
        raw: null,
      })),
    ]);
    const stage = buildStageBrief();
    let capList: any[] = Array.isArray((caps as any)?.capabilities)
      ? (caps as any).capabilities
      : Array.isArray(caps)
        ? caps
        : [];
    const toolNames = ((tools as any)?.tools || [])
      .map((t: any) => t?.function?.name || t?.name)
      .filter(Boolean);
    const agentIds = ((agents as any)?.data || []).map((a: any) => a.id).filter(Boolean);

    const liveRows = Array.isArray((liveAbilities as any)?.abilities)
      ? ((liveAbilities as any).abilities as Array<{ id: string; name?: string; status?: string }>)
      : [];
    const abilitySource = String((liveAbilities as any)?.source || 'unknown');

    // Start from LIVE Hive rows (never a packaged static list).
    const byId = new Map<string, { id: string; status: string; name?: string }>();
    for (const row of liveRows) {
      const id = String(row?.id || '').trim();
      if (!id) continue;
      byId.set(id, {
        id,
        name: row.name || id,
        status: String(row.status || 'LIVE').toUpperCase(),
      });
    }

    // Optional docs/sessions/ability_status.json overlay only:
    // can demote LIVE -> PARTIAL/MISSING and can add missing ids.
    try {
      const statusPath = path.join(
        vscode.workspace.workspaceFolders?.[0]?.uri.fsPath || '',
        'docs',
        'sessions',
        'ability_status.json'
      );
      if (fs.existsSync(statusPath)) {
        const overlay = JSON.parse(fs.readFileSync(statusPath, 'utf8'));
        const rows = Array.isArray(overlay)
          ? overlay
          : Array.isArray(overlay?.abilities)
            ? overlay.abilities
            : [];
        for (const row of rows) {
          const id = String(row?.id || '').trim();
          if (!id) continue;
          const overlayStatus = String(row.status || '').toUpperCase();
          const existing = byId.get(id);
          if (!existing) {
            byId.set(id, {
              id,
              name: row.name || id,
              status: overlayStatus || 'MISSING',
            });
            continue;
          }
          if (
            existing.status === 'LIVE' &&
            overlayStatus &&
            overlayStatus !== 'LIVE' &&
            ['PARTIAL', 'MISSING', 'STALE', 'OFF', 'DISABLED', 'ERROR'].includes(overlayStatus)
          ) {
            byId.set(id, { ...existing, status: overlayStatus, name: row.name || existing.name });
          }
        }
      }
    } catch {
      /* overlay optional */
    }

    const abilityStatus = Array.from(byId.values());

    // Merge live ability ids into capabilities so the Ops dock sees them.
    const capIds = new Set(
      capList
        .map((c: any) => String(c?.id || c?.name || c || '').trim())
        .filter(Boolean)
    );
    for (const row of abilityStatus) {
      if (!capIds.has(row.id)) {
        capList = [...capList, { id: row.id, name: row.name || row.id, kind: 'ability' }];
        capIds.add(row.id);
      }
    }

    this.post({
      command: 'bootstrap',
      version: UI_VERSION,
      stage,
      snap,
      capabilities: capList,
      tools: toolNames,
      agents: agentIds,
      hiveRoles: snap.hiveAgents || [],
      abilityStatus,
      abilitySource,
      coverage: (coverage as any)?.result?.coverage || (coverage as any)?.coverage || null,
      voiceProvider: 'realai-voice',
    });
  }

  private async onMessage(msg: any) {
    switch (msg?.command) {
      case 'ready':
        await this.pushBootstrap();
        break;
      case 'refresh':
        await this.pushBootstrap();
        break;
      case 'chat':
        await this.handleChat(String(msg.text || ''), Array.isArray(msg.history) ? msg.history : []);
        break;
      case 'runTool':
        await this.handleRunTool(String(msg.name || ''), msg.args || {});
        break;
      case 'runAbility':
        await this.handleRunAbility(String(msg.name || ''), msg.input, msg.context);
        break;
      case 'smoke':
        await this.handleSmoke();
        break;
      case 'local':
        await this.handleLocal(String(msg.kind || ''));
        break;
      case 'openExternal':
        if (msg.url) await vscode.env.openExternal(vscode.Uri.parse(String(msg.url)));
        break;
      default:
        break;
    }
  }

  private async handleLocal(kind: string) {
    if (kind === 'phase') {
      const [snap, ctx] = await Promise.all([
        collectStackSnapshot(this.client),
        buildContextSnapshot(),
      ]);
      const stage = snap.stage;
      const text = [
        `1) ${stage.phaseId} — ${stage.phaseTitle}`,
        `   tip: ${stage.tipLine}`,
        `2) apps/vscode realai-vscode@${stage.extensionVersion} · Console ui v${UI_VERSION}`,
        `3) Hive ${snap.hiveOk ? 'OK' : 'DOWN'} ${snap.baseUrl} · Vulkan ${snap.vulkanOk ? 'OK' : '?'} · Voice ${snap.voiceOk ? 'OK' : 'off'}`,
        `   tools ${snap.toolsCount} · agents ${snap.agentsCount} · caps ${snap.capabilitiesCount}`,
        `4) host ${ctx.hostMode || 'product'} · ${ctx.workspaceName} · home ${ctx.productHome || stage.productHome}`,
        `5) git ${ctx.gitBranch ? ctx.gitBranch + (ctx.gitDirty ? '*' : '') : 'n/a'}`,
        `6) abilities: ${stage.abilityRollup.slice(0, 6).join(' | ')}`,
      ].join('\n');
      this.lastResponse = text;
      this.post({ command: 'assistant', text });
      return;
    }
    if (kind === 'patches') {
      const text = auditAppsVscode().report;
      this.lastResponse = text;
      this.post({ command: 'assistant', text });
      return;
    }
    if (kind === 'repo') {
      try {
        const listing = await this.client.executeTool('workspace_list', { path: '.' });
        const entries = listing?.result?.entries || [];
        const root = listing?.result?.workspace || '';
        const lines = (entries as any[])
          .slice(0, 80)
          .map((e) => `- ${e.type === 'dir' ? 'dir ' : 'file'} ${e.name}`);
        const text = `Hive workspace_list for ${root}:\n` + lines.join('\n');
        this.lastResponse = text;
        this.post({ command: 'assistant', text });
      } catch (e: any) {
        this.post({ command: 'assistant', text: `Repo list failed: ${e?.message || e}` });
      }
      return;
    }
    if (kind === 'smoke') {
      await this.handleSmoke();
    }
  }

  private defaultArgsFor(name: string, args: Record<string, unknown>): Record<string, unknown> {
    if (args && Object.keys(args).length) return args;
    switch (name) {
      case 'workspace_list':
        return { path: '.' };
      case 'workspace_grep':
        return { pattern: 'RealAIConsolePanel|realai-vscode', path: 'apps/vscode', glob: '*.ts' };
      case 'workspace_read':
        return { path: 'apps/vscode/package.json', limit: 80 };
      case 'multi_agent_run':
        return {
          task: 'Audit apps/vscode and list 3 concrete file patches under apps/vscode only. No marketplace tips.',
          mode: 'pipeline',
        };
      default:
        return {};
    }
  }

  async handleRunAbility(name: string, input?: unknown, context?: Record<string, unknown>) {
    const ability = name.replace(/^ability\./, '');
    this.post({ command: 'status', text: `Running ability ${ability}…` });
    try {
      // Prefer tools/execute ability.* when present; fall back to /v1/abilities/run
      let result: any;
      try {
        result = await this.client.executeTool(
          name.startsWith('ability.') ? name : `ability.${ability}`,
          {
            input: input ?? `Console invoke ${ability}`,
            ...(context || {}),
          }
        );
      } catch {
        result = await this.client.runAbility(
          ability,
          input ?? `Console invoke ${ability}`,
          context || {}
        );
      }
      const text = `Ability \`${ability}\`\n\n\`\`\`json\n${JSON.stringify(result, null, 2).slice(0, 12000)}\n\`\`\``;
      this.lastResponse = text;
      this.post({ command: 'assistant', text });
    } catch (e: any) {
      this.post({ command: 'assistant', text: `Ability ${ability} failed: ${e?.message || e}` });
    }
  }

  async handleRunTool(name: string, args: Record<string, unknown>) {
    const resolved = String(name || '').trim();
    if (!resolved) {
      this.post({ command: 'assistant', text: 'No tool name provided.' });
      return;
    }
    if (resolved.startsWith('ability.') || resolved.startsWith('/')) {
      const ability = resolved.replace(/^\//, '').replace(/^ability\./, '');
      await this.handleRunAbility(ability, (args as any)?.input, args);
      return;
    }
    this.post({ command: 'status', text: `Running ${resolved}…` });
    const payload = this.defaultArgsFor(resolved, args || {});
    try {
      const result = await this.client.executeTool(resolved, payload);
      const text = `Tool \`${resolved}\`\n\n\`\`\`json\n${JSON.stringify(result, null, 2).slice(0, 12000)}\n\`\`\``;
      this.lastResponse = text;
      this.post({ command: 'assistant', text });
      return;
    } catch (e: any) {
      // Retry as ability.* tool / abilities/run
      try {
        await this.handleRunAbility(
          resolved,
          (args as any)?.input ?? `Console invoke ${resolved}`,
          args
        );
      } catch (e2: any) {
        this.post({
          command: 'assistant',
          text: `Tool ${resolved} failed: ${e?.message || e}\nAbility fallback failed: ${e2?.message || e2}`,
        });
      }
    }
  }

  /** Run a batch of safe catalog calls and report pass/fail in the feed. */
  async handleSmoke() {
    const checks: Array<{ label: string; run: () => Promise<unknown> }> = [
      { label: 'health', run: () => this.client.getHealth() },
      { label: 'hive', run: () => this.client.getHive() },
      { label: 'tools', run: () => this.client.listTools() },
      { label: 'agents', run: () => this.client.listAgents() },
      { label: 'capabilities', run: () => this.client.getCapabilities() },
      { label: 'workspace_list', run: () => this.client.executeTool('workspace_list', { path: '.' }) },
      { label: 'self_heal_status', run: () => this.client.executeTool('self_heal_status', {}) },
      { label: 'list_agents', run: () => this.client.executeTool('list_agents', {}) },
      { label: 'ability_coverage', run: () => this.client.executeTool('ability_coverage', {}) },
      {
        label: 'ability.chat_completion',
        run: () =>
          this.client.executeTool('ability.chat_completion', {
            input: 'Reply with: console smoke ok',
          }),
      },
      {
        label: 'abilities/run code_generation',
        run: () => this.client.runAbility('code_generation', 'return 1+1 in one line', {}),
      },
    ];
    const lines: string[] = ['Console smoke test (abilities / tools / agents)', ''];
    let pass = 0;
    for (const c of checks) {
      try {
        const result = await c.run();
        const size = JSON.stringify(result ?? null).length;
        lines.push(`PASS  ${c.label}  (${size} bytes)`);
        pass++;
      } catch (e: any) {
        lines.push(`FAIL  ${c.label}  ${e?.message || e}`);
      }
    }
    lines.push('', `Result: ${pass}/${checks.length} passed`);
    const text = lines.join('\n');
    this.lastResponse = text;
    this.post({ command: 'assistant', text });
    await this.pushBootstrap();
  }

  private async handleChat(text: string, history: ThreadMsg[]) {
    const trimmed = text.trim();
    if (!trimmed) return;

    // Local console shortcuts (deterministic)
    const low = trimmed.toLowerCase();
    if (low === '/phase' || low === '/where') {
      await this.handleLocal('phase');
      return;
    }
    if (low === '/patches' || low === '/audit' || (/concrete\s+patches/.test(low))) {
      await this.handleLocal('patches');
      return;
    }
    if (low === '/repo' || low === '/read') {
      await this.handleLocal('repo');
      return;
    }
    if (low.startsWith('/multi')) {
      const task = trimmed.replace(/^\/multi\s*/i, '').trim();
      if (!task) {
        this.post({ command: 'assistant', text: 'Usage: /multi <task>' });
        return;
      }
      const stage = buildStageBrief();
      const mode = detectWorkspaceMode();
      const grounded = [
        mode.hostMode === 'foreign'
          ? `Host mode: FOREIGN REPO. Workspace ${mode.workspaceName} at ${mode.workspaceRoot}. Product home ${mode.productHome}. Hive :8001.`
          : `Product: realai-vscode@${stage.extensionVersion} in ${stage.productHome}.`,
        mode.hostMode === 'foreign'
          ? 'Scope: THIS workspace (full-stack). Do not assume RealAI-clean layout.'
          : 'Scope: apps/vscode only unless task says otherwise.',
        `Task: ${task}`,
        'Forbidden: Live Share, marketplace installs, update VS Code, Apache Hive jokes.',
      ].join('\n');
      this.post({ command: 'status', text: 'multi-agent pipeline…' });
      try {
        const result = await this.client.multiAgentRun(grounded);
        const text = `Multi-agent result\n\n\`\`\`json\n${JSON.stringify(result, null, 2).slice(0, 12000)}\n\`\`\``;
        this.lastResponse = text;
        this.post({ command: 'assistant', text });
      } catch (e: any) {
        this.post({ command: 'assistant', text: `Multi-agent failed: ${e?.message || e}` });
      }
      return;
    }

    // Match browser /console: send the thread as-is (Hive injects RealAI Bot system).
    // Keep light editor context only when user asks about the current file/selection.
    const wantsEditorCtx =
      /\b(this file|selection|current file|open file|refactor|explain)\b/i.test(trimmed);
    const messages: ChatMessage[] = [
      ...history
        .filter((m) => m.role === 'user' || m.role === 'assistant')
        .slice(-16)
        .map((m) => ({ role: m.role as 'user' | 'assistant', content: m.content })),
      { role: 'user', content: trimmed },
    ];
    if (wantsEditorCtx) {
      try {
        const ctx = await buildContextSnapshot();
        messages.unshift({ role: 'system', content: ctx.systemPrompt + '\n\n' + ctx.userContextBlock });
      } catch {
        /* ignore */
      }
    }

    // Browser console is non-streaming + tools/voice on.
    this.post({ command: 'status', text: 'Hive chat…' });
    try {
      const full = await this.client.chatFull(messages, {
        tools: true,
        memory: true,
        temperature: 0.35,
        maxTokens: 1024,
      });
      const reply = (full.content || '').trim() || '(empty reply)';
      this.lastResponse = reply;
      this.post({
        command: 'assistant',
        text: reply,
        voice: full.voice || null,
        speak: this.client.voiceEnabled,
      });
    } catch (e: any) {
      this.post({ command: 'assistant', text: `Error: ${e?.message || e}` });
    }
  }
}
