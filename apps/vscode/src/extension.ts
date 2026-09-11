import * as vscode from 'vscode';
import { RealAIClient } from './realaiClient';
import { RealAIChatPanel } from './chatPanel';
import { RealAIConsolePanel } from './consolePanel';
import { buildContextSnapshot } from './contextPack';
import { RealAIHubViewProvider } from './hubView';
import { collectStackSnapshot } from './stackStatus';
import { buildStageBrief } from './stageContext';
import { RealAILanguageModelChatProvider, REALAI_LM_VENDOR } from './lmChatProvider';
import { resolveProductHome, detectWorkspaceMode } from './workspaceMode';

let client: RealAIClient;
let statusBar: vscode.StatusBarItem;
let hub: RealAIHubViewProvider;
let lmProvider: RealAILanguageModelChatProvider;

function getConfigBaseUrl(): string {
  return (
    vscode.workspace.getConfiguration('realai').get<string>('baseUrl') ||
    'http://127.0.0.1:8001'
  );
}

function getConfigModel(): string {
  return (
    vscode.workspace.getConfiguration('realai').get<string>('model') ||
    'realai-hive'
  );
}

function refreshClientFromConfig() {
  const cfg = vscode.workspace.getConfiguration('realai');
  client = new RealAIClient(getConfigBaseUrl());
  client.setModel(getConfigModel());
  client.defaultAgentId = (cfg.get<string>('agentId') || '').trim();
  client.memoryEnabled = cfg.get<boolean>('memory') ?? true;
  // Match browser /console defaults: tools + voice on
  client.toolsEnabled = cfg.get<boolean>('tools') ?? true;
  client.voiceEnabled = cfg.get<boolean>('voiceSpeak') ?? true;
}


function workspaceRootPath(): string {
  return vscode.workspace.workspaceFolders?.[0]?.uri.fsPath || process.cwd();
}

function realaiTerminalEnv(): Record<string, string> {
  const productHome =
    vscode.workspace.getConfiguration('realai').get<string>('productHome') ||
    resolveProductHome(workspaceRootPath());
  const root = workspaceRootPath();
  const env: Record<string, string> = {
    ...process.env as Record<string, string>,
    REALAI_HOME: productHome,
    REALAI_WORKSPACE: root,
  };
  // Prefer global RealAI scripts on PATH when install_global placed them under productHome\\scripts or .local\\bin
  const extras = [
    `${productHome}\\scripts`,
    `${productHome}\\.local\\bin`,
    `${productHome}\\bin`,
  ];
  const pathKey = process.platform === 'win32' ? 'Path' : 'PATH';
  const cur = env[pathKey] || env.PATH || '';
  env[pathKey] = [...extras, cur].filter(Boolean).join(process.platform === 'win32' ? ';' : ':');
  return env;
}

async function openRealAITerminal(send?: string): Promise<vscode.Terminal> {
  const root = workspaceRootPath();
  const term = vscode.window.createTerminal({
    name: 'RealAI',
    cwd: root,
    env: realaiTerminalEnv(),
  });
  term.show(true);
  if (send) {
    // Give the shell a moment to start before sending.
    setTimeout(() => term.sendText(send, true), 400);
  }
  return term;
}

async function ensureConsole(ctx: vscode.ExtensionContext): Promise<RealAIConsolePanel> {
  return RealAIConsolePanel.createOrShow(ctx, client);
}

async function ensureChatPanel(ctx: vscode.ExtensionContext): Promise<RealAIChatPanel> {
  // Legacy panel kept for selection workflows that still use sendMessage helpers.
  RealAIChatPanel.createOrShow(ctx, client);
  const panel = RealAIChatPanel.instance;
  if (!panel) throw new Error('Failed to open RealAI Chat panel');
  return panel;
}

async function runPromptOnSelection(
  ctx: vscode.ExtensionContext,
  prefix: string,
  emptyMessage: string
) {
  const editor = vscode.window.activeTextEditor;
  if (!editor) {
    vscode.window.showWarningMessage('Open a file and select code first.');
    return;
  }
  const selection = editor.document.getText(editor.selection);
  if (!selection.trim()) {
    vscode.window.showWarningMessage(emptyMessage);
    return;
  }
  const language = editor.document.languageId;
  const file = vscode.workspace.asRelativePath(editor.document.uri);
  const panel = await ensureChatPanel(ctx);
  await panel.sendMessage(
    `${prefix}\n\nFile: ${file}\n\n\`\`\`${language}\n${selection}\n\`\`\``
  );
}

async function openJsonDoc(title: string, data: unknown) {
  const doc = await vscode.workspace.openTextDocument({
    content: `// ${title}\n` + JSON.stringify(data, null, 2),
    language: 'json',
  });
  await vscode.window.showTextDocument(doc, { preview: true });
}

export function activate(context: vscode.ExtensionContext) {
  refreshClientFromConfig();

  hub = new RealAIHubViewProvider(context, () => client);
  context.subscriptions.push(
    vscode.window.registerWebviewViewProvider(RealAIHubViewProvider.viewType, hub)
  );

  lmProvider = new RealAILanguageModelChatProvider(() => client);
  context.subscriptions.push(
    vscode.lm.registerLanguageModelChatProvider(REALAI_LM_VENDOR, lmProvider)
  );

  statusBar = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Right, 100);
  statusBar.command = 'realai.showStatus';
  statusBar.text = '$(hubot) RealAI';
  statusBar.tooltip = 'RealAI Ultimate — click for stack status';
  statusBar.show();
  context.subscriptions.push(statusBar);

  context.subscriptions.push(
    vscode.workspace.onDidChangeConfiguration((e) => {
      if (e.affectsConfiguration('realai')) {
        refreshClientFromConfig();
        void hub.refresh();
        lmProvider.refresh();
        if (RealAIConsolePanel.current) {
          void ensureConsole(context);
        }
      }
    })
  );

  const commands: Array<[string, (...args: any[]) => any]> = [
    ['realai.openChat', async () => {
      await ensureConsole(context);
    }],
    ['realai.openBrowserConsole', async () => {
      const base = getConfigBaseUrl().replace(/\/$/, '');
      await vscode.env.openExternal(vscode.Uri.parse(`${base}/console`));
    }],
    ['realai.openLegacyChat', async () => {
      await ensureChatPanel(context);
    }],
    ['realai.refreshHub', async () => {
      await hub.refresh();
      const snap = hub.getLatest();
      vscode.window.showInformationMessage(snap?.summaryLine || 'Hub refreshed');
    }],
    ['realai.refreshAbilities', async () => {
      refreshClientFromConfig();
      const panel = await ensureConsole(context);
      await panel.refreshBootstrap();
      vscode.window.showInformationMessage('RealAI abilities refreshed from Hive.');
    }],
    ['realai.openTerminal', async () => {
      await openRealAITerminal();
      const mode = detectWorkspaceMode();
      vscode.window.showInformationMessage(
        `RealAI terminal · WORKSPACE=${mode.workspaceRoot} · HOME=${mode.productHome}`
      );
    }],
    ['realai.terminalChat', async () => {
      await openRealAITerminal('realai');
    }],
    ['realai.terminalCode', async () => {
      await openRealAITerminal('realai-code');
    }],
    ['realai.refreshContext', async () => {
      const panel = await ensureChatPanel(context);
      await panel.refreshContext(true);
      const snap = await buildContextSnapshot();
      vscode.window.showInformationMessage(`RealAI context: ${snap.summaryLine}`);
    }],
    ['realai.whereAreWe', async () => {
      const panel = await ensureConsole(context);
      await panel.runLocal('phase');
    }],
    ['realai.readRepo', async () => {
      const panel = await ensureConsole(context);
      await panel.runLocal('repo');
    }],
    ['realai.extensionAudit', async () => {
      const panel = await ensureConsole(context);
      await panel.runLocal('patches');
    }],
    ['realai.consoleSmoke', async () => {
      const panel = await ensureConsole(context);
      await panel.runLocal('smoke');
    }],
    ['realai.multiAgent', async () => {
      const task = await vscode.window.showInputBox({
        prompt: 'Multi-agent task for RealAI Hive',
        placeHolder: 'e.g. Audit apps/vscode and propose the next 3 patches',
      });
      if (!task?.trim()) return;
      const panel = await ensureConsole(context);
      await panel.runChat(`/multi ${task.trim()}`);
    }],
    ['realai.runTool', async () => {
      let tools: any;
      try {
        tools = await client.listTools();
      } catch (e: any) {
        vscode.window.showErrorMessage(`List tools failed: ${e?.message || e}`);
        return;
      }
      const names = (tools.tools || [])
        .map((t: any) => t?.function?.name || t?.name)
        .filter(Boolean) as string[];
      const picked = await vscode.window.showQuickPick(names, {
        placeHolder: 'Run Hive tool',
        matchOnDescription: true,
      });
      if (!picked) return;
      const argsRaw = await vscode.window.showInputBox({
        prompt: `JSON arguments for ${picked} (or empty)`,
        value: '{}',
      });
      let args: Record<string, unknown> = {};
      try {
        args = argsRaw ? JSON.parse(argsRaw) : {};
      } catch {
        vscode.window.showErrorMessage('Arguments must be valid JSON');
        return;
      }
      const panel = await ensureConsole(context);
      // Reuse console tool runner via webview message protocol
      await (panel as any).handleRunTool(picked, args);
    }],
    ['realai.explainCode', async () => {
      await runPromptOnSelection(
        context,
        'Explain this code in the context of this RealAI repo. Cover behavior, nearby modules, risks:',
        'Select the code you want explained.'
      );
    }],
    ['realai.refactorCode', async () => {
      await runPromptOnSelection(
        context,
        'Refactor this code for clarity in this repo. Keep behavior the same and show the improved version:',
        'Select the code you want refactored.'
      );
    }],
    ['realai.generateTests', async () => {
      await runPromptOnSelection(
        context,
        'Write focused unit tests for this code. Match project test style when obvious:',
        'Select the code you want tests for.'
      );
    }],
    ['realai.generateDocs', async () => {
      await runPromptOnSelection(
        context,
        'Write concise documentation for this code:',
        'Select the code you want documented.'
      );
    }],
    ['realai.fixBug', async () => {
      await runPromptOnSelection(
        context,
        'Find bugs and failure modes in this code. Suggest concrete fixes:',
        'Select the code you want reviewed.'
      );
    }],
    ['realai.optimizeCode', async () => {
      await runPromptOnSelection(
        context,
        'Optimize this code for performance/simplicity. Explain changes:',
        'Select the code you want optimized.'
      );
    }],
    ['realai.insertResponse', async () => {
      const text =
        RealAIConsolePanel.current?.lastAssistant?.trim() ||
        RealAIChatPanel.instance?.lastResponse?.trim();
      if (!text) {
        vscode.window.showWarningMessage('No RealAI response to insert yet.');
        return;
      }
      const editor = vscode.window.activeTextEditor;
      if (!editor) {
        vscode.window.showWarningMessage('Open an editor to insert the response.');
        return;
      }
      await editor.edit((builder) => {
        if (editor.selection.isEmpty) builder.insert(editor.selection.active, text);
        else builder.replace(editor.selection, text);
      });
    }],
    ['realai.clearChat', async () => {
      await ensureConsole(context);
      vscode.window.showInformationMessage('Open Console and click + New thread to clear.');
    }],
    ['realai.checkHealth', async () => {
      try {
        statusBar.text = '$(sync~spin) RealAI';
        const snap = await collectStackSnapshot(client);
        statusBar.text = snap.ok ? '$(hubot) RealAI' : '$(warning) RealAI';
        statusBar.tooltip = snap.summaryLine;
        vscode.window.showInformationMessage(snap.summaryLine);
        await hub.refresh();
      } catch (e: any) {
        statusBar.text = '$(warning) RealAI';
        vscode.window.showErrorMessage(`Health failed: ${e?.message || e}`);
      }
    }],
    ['realai.showStatus', async () => {
      const snap = await collectStackSnapshot(client);
      statusBar.text = snap.ok ? '$(hubot) RealAI' : '$(warning) RealAI';
      statusBar.tooltip = snap.summaryLine;
      await openJsonDoc('RealAI stack status', snap);
      await hub.refresh();
    }],
    ['realai.selectModel', async () => {
      try {
        const listed = await client.listModels();
        const ids = (listed.data || []).map((m) => m.id).filter(Boolean);
        const picks = ids.length ? ids : [client.selectedModel, 'realai-hive'];
        const chosen = await vscode.window.showQuickPick(picks, {
          placeHolder: 'Select RealAI model',
        });
        if (!chosen) return;
        client.setModel(chosen);
        await vscode.workspace
          .getConfiguration('realai')
          .update('model', chosen, vscode.ConfigurationTarget.Global);
        vscode.window.showInformationMessage(`RealAI model set to ${chosen}`);
      } catch (e: any) {
        // models endpoint can have duplicate casing keys; allow manual entry
        const chosen = await vscode.window.showInputBox({
          prompt: `Model id (list failed: ${e?.message || e})`,
          value: client.selectedModel,
        });
        if (!chosen) return;
        client.setModel(chosen);
        await vscode.workspace
          .getConfiguration('realai')
          .update('model', chosen, vscode.ConfigurationTarget.Global);
      }
    }],
    ['realai.showCapabilities', async () => {
      await openJsonDoc('RealAI capabilities', await client.getCapabilities());
    }],
    ['realai.listTools', async () => {
      await openJsonDoc('RealAI tools', await client.listTools());
    }],
    ['realai.listAgents', async () => {
      const [hive, agents] = await Promise.all([client.getHive(), client.listAgents()]);
      await openJsonDoc('RealAI agents', { hive, agents });
    }],
    ['realai.showSelfHeal', async () => {
      await openJsonDoc('RealAI self-heal', await client.getSelfHealStatus());
    }],
    ['realai.showLora', async () => {
      await openJsonDoc('RealAI LoRA', await client.getLora());
    }],
    ['realai.showRecovery', async () => {
      await openJsonDoc('RealAI recovery', await client.getRecovery());
    }],
    ['realai.showPhase', async () => {
      const stage = buildStageBrief();
      await openJsonDoc('RealAI stage brief', stage);
      const panel = await ensureConsole(context);
      await panel.runLocal('phase');
    }],
    ['realai.orchestrateAgents', async () => {
      await vscode.commands.executeCommand('realai.multiAgent');
    }],
  ];

  for (const [id, handler] of commands) {
    context.subscriptions.push(vscode.commands.registerCommand(id, handler));
  }

  // Boot status
  void collectStackSnapshot(client).then((snap) => {
    statusBar.text = snap.ok ? '$(hubot) RealAI' : '$(warning) RealAI';
    statusBar.tooltip = snap.summaryLine;
  });
  void hub.refresh();
}

export function deactivate() {}
