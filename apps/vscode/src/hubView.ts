import * as fs from 'fs';
import * as path from 'path';
import * as vscode from 'vscode';
import { RealAIClient } from './realaiClient';
import { buildStageBrief } from './stageContext';
import { collectStackSnapshot, StackSnapshot } from './stackStatus';

export class RealAIHubViewProvider implements vscode.WebviewViewProvider {
  public static readonly viewType = 'realai.hub';

  private view?: vscode.WebviewView;
  private latest?: StackSnapshot;

  constructor(
    private readonly ctx: vscode.ExtensionContext,
    private readonly getClient: () => RealAIClient
  ) {}

  resolveWebviewView(
    webviewView: vscode.WebviewView,
    _context: vscode.WebviewViewResolveContext,
    _token: vscode.CancellationToken
  ) {
    this.view = webviewView;
    webviewView.webview.options = {
      enableScripts: true,
      localResourceRoots: [
        vscode.Uri.file(path.join(this.ctx.extensionPath, 'webview')),
        vscode.Uri.file(path.join(this.ctx.extensionPath, 'media')),
      ],
    };
    webviewView.webview.html = this.getHtml();
    webviewView.webview.onDidReceiveMessage(async (msg) => {
      if (msg?.command === 'ready' || msg?.command === 'refresh') {
        await this.refresh();
        return;
      }
      if (msg?.command === 'run' && msg.id) {
        await vscode.commands.executeCommand(String(msg.id));
      }
    });
    void this.refresh();
  }

  async refresh() {
    try {
      this.latest = await collectStackSnapshot(this.getClient());
      this.view?.webview.postMessage({ command: 'snapshot', snapshot: this.latest });
      if (this.view) {
        this.view.description = this.latest.ok ? 'online' : 'offline';
      }
    } catch (e: any) {
      const stage = buildStageBrief();
      this.view?.webview.postMessage({
        command: 'snapshot',
        snapshot: {
          ok: false,
          baseUrl: this.getClient().getBaseUrl(),
          hiveOk: false,
          vulkanOk: false,
          hiveAgents: [],
          hiveAgentCount: 0,
          toolsCount: 0,
          agentsCount: 0,
          capabilitiesCount: 0,
          voiceOk: false,
          voiceUrl: 'http://127.0.0.1:8890',
          stage: {
            ...stage,
            tipLine: String(e?.message || e),
          },
          errors: [String(e?.message || e)],
          summaryLine: 'hub refresh failed',
          collectedAt: new Date().toISOString(),
        },
      });
    }
  }

  getLatest(): StackSnapshot | undefined {
    return this.latest;
  }

  private getHtml(): string {
    const htmlPath = path.join(this.ctx.extensionPath, 'webview', 'hub.html');
    try {
      const raw = fs.readFileSync(htmlPath, 'utf8');
      return raw.replace('</head>', `<!-- hub ${Date.now()} -->\n</head>`);
    } catch (e: any) {
      return `<html><body style="padding:12px;font-family:sans-serif">Hub failed to load: ${String(
        e?.message || e
      )}</body></html>`;
    }
  }
}
