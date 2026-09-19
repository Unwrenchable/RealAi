"use strict";
var __createBinding = (this && this.__createBinding) || (Object.create ? (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    var desc = Object.getOwnPropertyDescriptor(m, k);
    if (!desc || ("get" in desc ? !m.__esModule : desc.writable || desc.configurable)) {
      desc = { enumerable: true, get: function() { return m[k]; } };
    }
    Object.defineProperty(o, k2, desc);
}) : (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    o[k2] = m[k];
}));
var __setModuleDefault = (this && this.__setModuleDefault) || (Object.create ? (function(o, v) {
    Object.defineProperty(o, "default", { enumerable: true, value: v });
}) : function(o, v) {
    o["default"] = v;
});
var __importStar = (this && this.__importStar) || (function () {
    var ownKeys = function(o) {
        ownKeys = Object.getOwnPropertyNames || function (o) {
            var ar = [];
            for (var k in o) if (Object.prototype.hasOwnProperty.call(o, k)) ar[ar.length] = k;
            return ar;
        };
        return ownKeys(o);
    };
    return function (mod) {
        if (mod && mod.__esModule) return mod;
        var result = {};
        if (mod != null) for (var k = ownKeys(mod), i = 0; i < k.length; i++) if (k[i] !== "default") __createBinding(result, mod, k[i]);
        __setModuleDefault(result, mod);
        return result;
    };
})();
Object.defineProperty(exports, "__esModule", { value: true });
exports.activate = activate;
exports.deactivate = deactivate;
const vscode = __importStar(require("vscode"));
const realaiClient_1 = require("./realaiClient");
const chatPanel_1 = require("./chatPanel");
const DEFAULT_BASE = 'http://127.0.0.1:8000';
const DEFAULT_MODEL = 'realai-2.0';
let client;
function cfg() {
    return vscode.workspace.getConfiguration('realai');
}
function ensureClient() {
    const baseUrl = cfg().get('baseUrl') || DEFAULT_BASE;
    const model = cfg().get('model') || DEFAULT_MODEL;
    if (!client) {
        client = new realaiClient_1.RealAIClient(baseUrl);
    }
    else {
        // RealAIClient has no setter for baseUrl; recreate if URL changed
        client = new realaiClient_1.RealAIClient(baseUrl);
    }
    client.setModel(model);
    return client;
}
function activate(context) {
    ensureClient();
    const commands = [
        [
            'realai.openChat',
            () => {
                chatPanel_1.RealAIChatPanel.createOrShow(context, ensureClient());
            },
        ],
        [
            'realai.chatSelection',
            async () => {
                const editor = vscode.window.activeTextEditor;
                const selected = editor?.document.getText(editor.selection)?.trim();
                const text = selected ||
                    (await vscode.window.showInputBox({
                        prompt: 'Ask RealAI',
                        placeHolder: 'Explain this code, fix a bug, …',
                    }));
                if (!text)
                    return;
                chatPanel_1.RealAIChatPanel.createOrShow(context, ensureClient());
                const panel = chatPanel_1.RealAIChatPanel.instance;
                if (panel) {
                    panel.setInput(text);
                    await panel.sendMessage(text);
                }
            },
        ],
        [
            'realai.insertResponse',
            async () => {
                const editor = vscode.window.activeTextEditor;
                const reply = chatPanel_1.RealAIChatPanel.instance?.lastResponse?.trim();
                if (!editor || !reply) {
                    vscode.window.showWarningMessage('No RealAI response to insert.');
                    return;
                }
                await editor.edit((eb) => {
                    if (editor.selection.isEmpty) {
                        eb.insert(editor.selection.active, reply);
                    }
                    else {
                        eb.replace(editor.selection, reply);
                    }
                });
            },
        ],
        [
            'realai.setModel',
            async () => {
                const c = ensureClient();
                let models = [DEFAULT_MODEL, 'realai-1.0', 'qwen2.5-coder'];
                try {
                    const listed = await c.listModels();
                    const ids = (listed?.data || []).map((m) => m.id).filter(Boolean);
                    if (ids.length)
                        models = ids;
                }
                catch {
                    /* offline — keep defaults */
                }
                const picked = await vscode.window.showQuickPick(models, {
                    placeHolder: 'Select RealAI model',
                });
                if (!picked)
                    return;
                c.setModel(picked);
                await cfg().update('model', picked, vscode.ConfigurationTarget.Global);
                vscode.window.showInformationMessage(`RealAI model: ${picked}`);
                chatPanel_1.RealAIChatPanel.postActivity(`Model → ${picked}`);
            },
        ],
        [
            'realai.health',
            async () => {
                const c = ensureClient();
                try {
                    const h = await c.getHealth();
                    vscode.window.showInformationMessage(`RealAI health: ${h.status}${h.model ? ` (${h.model})` : ''} @ ${cfg().get('baseUrl') || DEFAULT_BASE}`);
                }
                catch (e) {
                    vscode.window.showErrorMessage(`RealAI unreachable at ${cfg().get('baseUrl') || DEFAULT_BASE}: ${e?.message || e}`);
                }
            },
        ],
        [
            'realai.setBaseUrl',
            async () => {
                const current = cfg().get('baseUrl') || DEFAULT_BASE;
                const next = await vscode.window.showInputBox({
                    prompt: 'RealAI API base URL',
                    value: current,
                    placeHolder: 'http://127.0.0.1:8000 or http://127.0.0.1:8001',
                });
                if (!next)
                    return;
                await cfg().update('baseUrl', next.trim(), vscode.ConfigurationTarget.Global);
                client = new realaiClient_1.RealAIClient(next.trim());
                client.setModel(cfg().get('model') || DEFAULT_MODEL);
                vscode.window.showInformationMessage(`RealAI base URL → ${next.trim()}`);
            },
        ],
    ];
    for (const [id, handler] of commands) {
        context.subscriptions.push(vscode.commands.registerCommand(id, handler));
    }
    // Status bar: quick open chat
    const status = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Right, 100);
    status.text = '$(hubot) RealAI';
    status.tooltip = 'Open RealAI Chat';
    status.command = 'realai.openChat';
    status.show();
    context.subscriptions.push(status);
}
function deactivate() {
    /* nothing */
}
//# sourceMappingURL=extension.js.map