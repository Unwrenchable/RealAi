import * as fs from 'fs';
import * as path from 'path';
import * as vscode from 'vscode';
import { buildStageBrief } from './stageContext';

export interface ConcretePatch {
  path: string;
  change: string;
  why: string;
  status: 'proposed' | 'already-landed';
}

function exists(root: string, rel: string): boolean {
  return fs.existsSync(path.join(root, rel));
}

function read(root: string, rel: string): string {
  try {
    return fs.readFileSync(path.join(root, rel), 'utf8');
  } catch {
    return '';
  }
}

/** Deterministic audit of apps/vscode - no GGUF, no marketplace fluff. */
export function auditAppsVscode(workspaceRoot?: string): {
  root: string;
  version: string;
  patches: ConcretePatch[];
  report: string;
} {
  const folder = vscode.workspace.workspaceFolders?.[0]?.uri.fsPath;
  const root = workspaceRoot || folder || process.cwd();
  const stage = buildStageBrief(root);
  const version = stage.extensionVersion;
  const patches: ConcretePatch[] = [];

  const phases = read(root, 'docs/sessions/PHASES.md');
  const chatPanel = read(root, 'apps/vscode/src/chatPanel.ts');
  const client = read(root, 'apps/vscode/src/realaiClient.ts');
  const indexHtml = read(root, 'apps/vscode/webview/index.html');
  const lmChat = read(root, 'apps/vscode/src/lmChatProvider.ts');
  const workspaceMode = read(root, 'apps/vscode/src/workspaceMode.ts');
  const contextPack = read(root, 'apps/vscode/src/contextPack.ts');
  const consolePanel = read(root, 'apps/vscode/src/consolePanel.ts');
  const pkg = read(root, 'apps/vscode/package.json');

  // Tip line: first ~800 chars / Current tip section
  const tipSlice = (() => {
    const m = phases.match(/\*\*Current tip of product work:\*\*[^\n]*/);
    return m ? m[0] : phases.slice(0, 800);
  })();

  // 1) PHASES tip
  if (/Phase\s+I\b/.test(tipSlice) && /1\.2\.5/.test(tipSlice) && !/Phase\s+J\b/.test(tipSlice)) {
    patches.push({
      path: 'docs/sessions/PHASES.md',
      change: `Update Current tip from Phase I / 1.2.5 to live stage (realai-vscode@${version}).`,
      why: 'Hub /phase tip looked stale while the extension already moved on.',
      status: 'proposed',
    });
  } else if (/Phase\s+J\b/.test(tipSlice) && /1\.2\.10/.test(tipSlice)) {
    patches.push({
      path: 'docs/sessions/PHASES.md',
      change: 'Keep Current tip on Phase J / 1.2.10 (any-repo full-stack Hive).',
      why: 'Tip matches the live console/chat stage narrative.',
      status: 'already-landed',
    });
  }

  // 2) Free-form "list concrete patches" must not hit ungrounded chat
  if (!/concrete\s+patches|auditAppsVscode|\/patches/.test(chatPanel)) {
    patches.push({
      path: 'apps/vscode/src/chatPanel.ts',
      change:
        'Route "list 3 concrete patches" / apps/vscode audit asks to a local deterministic auditor (not free chat).',
      why: 'Free prose was returning generic Integrate multi-agent / Enhance context fluff.',
      status: 'proposed',
    });
  } else {
    patches.push({
      path: 'apps/vscode/src/chatPanel.ts',
      change: 'Keep /patches + audit intent on the local auditor path.',
      why: 'Prevents regression to ungrounded GGUF answers.',
      status: 'already-landed',
    });
  }

  // 3) IDE chat must keep X-RealAI-Tools: off
  if (!client.includes("X-RealAI-Tools'] = tools ? 'on' : 'off'") && !client.includes('X-RealAI-Tools')) {
    patches.push({
      path: 'apps/vscode/src/realaiClient.ts',
      change: "Always send X-RealAI-Tools on|off explicitly (off by default for IDE chat).",
      why: 'Hive live_exec hijacks prompts containing git/command/run when tools default on.',
      status: 'proposed',
    });
  } else {
    patches.push({
      path: 'apps/vscode/src/realaiClient.ts',
      change: 'Retain explicit X-RealAI-Tools: off for normal IDE chat.',
      why: 'Required so /phase-style prose is not swallowed by live_exec.',
      status: 'already-landed',
    });
  }

  // 4) Welcome hint /patches + chip version vs live package
  const welcomeHasPatches =
    /\/patches/.test(indexHtml) &&
    (/welcome/i.test(indexHtml) || /Look for/.test(indexHtml) || /Try <code>\/phase/.test(indexHtml));
  if (welcomeHasPatches) {
    patches.push({
      path: 'apps/vscode/webview/index.html',
      change: 'Keep /patches in welcome hint next to /phase /repo /tools.',
      why: 'Users discover the deterministic auditor instead of free-form fluff.',
      status: 'already-landed',
    });
  } else {
    patches.push({
      path: 'apps/vscode/webview/index.html',
      change: 'Surface /patches in the welcome hint next to /phase /repo /tools.',
      why: 'Users discover the deterministic auditor instead of free-form fluff.',
      status: 'proposed',
    });
  }

  const chipVersions = [...indexHtml.matchAll(/Look for <b>v([^<]+)<\/b> chips/g)].map((m) => m[1]);
  const staleChip = chipVersions.find((v) => v !== version);
  if (staleChip) {
    patches.push({
      path: 'apps/vscode/webview/index.html',
      change: `Bump welcome chip text from v${staleChip} to live v${version}.`,
      why: 'Welcome still advertises an older UI build than package.json.',
      status: 'proposed',
    });
  }

  // 5) package.json extensionAudit command
  if (pkg.includes('realai.extensionAudit')) {
    patches.push({
      path: 'apps/vscode/package.json',
      change: 'Keep RealAI: Extension Audit (realai.extensionAudit) wired to /patches.',
      why: 'Command Palette parity with Hub/Chat slash flow.',
      status: 'already-landed',
    });
  } else {
    patches.push({
      path: 'apps/vscode/package.json',
      change: 'Add RealAI: Extension Audit (3 concrete patches) command wired to /patches.',
      why: 'Command Palette parity with Hub/Chat slash flow.',
      status: 'proposed',
    });
  }

  // 6) lmChatProvider agent dispatch
  const hasRunAgent = /\.runAgent\s*\(/.test(lmChat) || /runAgent\s*\(/.test(lmChat);
  const hasCoderOrDispatch =
    /coder-fullstack/.test(lmChat) || /chatDispatchAgents/.test(lmChat) || /CODER_FULLSTACK/.test(lmChat);
  if (hasRunAgent && hasCoderOrDispatch) {
    patches.push({
      path: 'apps/vscode/src/lmChatProvider.ts',
      change: 'Chat coder/agent dispatches POST /v1/agents/run',
      why: 'Coder-fullstack / agent picks must hit Hive agents, not plain chat.',
      status: 'already-landed',
    });
  } else {
    patches.push({
      path: 'apps/vscode/src/lmChatProvider.ts',
      change: 'Wire coder-fullstack / chatDispatchAgents to client.runAgent (POST /v1/agents/run).',
      why: 'Without it, agent picks fall back to ungrounded plain-model chat.',
      status: 'proposed',
    });
  }

  // 7) Foreign-repo workspace mode
  const hasWorkspaceMode = exists(root, 'apps/vscode/src/workspaceMode.ts') && /hostMode/.test(workspaceMode);
  const hasContextHost = /hostMode/.test(contextPack);
  if (hasWorkspaceMode && hasContextHost) {
    patches.push({
      path: 'apps/vscode/src/workspaceMode.ts',
      change: 'Keep foreign-repo hostMode detection feeding contextPack.',
      why: 'Any-repo full-stack needs FOREIGN vs product home separation.',
      status: 'already-landed',
    });
  } else {
    patches.push({
      path: 'apps/vscode/src/workspaceMode.ts',
      change: 'Add workspaceMode hostMode + wire contextPack foreign-repo prompts.',
      why: 'Any-repo full-stack needs FOREIGN vs product home separation.',
      status: 'proposed',
    });
  }

  // 8) Console UI_VERSION drift (informational proposed only when mismatched)
  const uiVer = consolePanel.match(/UI_VERSION\s*=\s*['"]([^'"]+)['"]/);
  if (uiVer && uiVer[1] !== version) {
    patches.push({
      path: 'apps/vscode/src/consolePanel.ts',
      change: `Align UI_VERSION '${uiVer[1]}' with package ${version}.`,
      why: 'Console title/banner should match the installed extension version.',
      status: 'proposed',
    });
  }

  // Prefer up to 3 items: proposed first, then landed. No fake filler.
  const proposed = patches.filter((p) => p.status === 'proposed');
  const landed = patches.filter((p) => p.status === 'already-landed');
  const chosen = [...proposed, ...landed].slice(0, 3);

  const report = [
    `Concrete patches for apps/vscode (realai-vscode@${version})`,
    `Workspace: ${root}`,
    ``,
    ...chosen.map((p, i) => {
      const tag = p.status === 'already-landed' ? 'LANDED' : 'PROPOSED';
      return [
        `${i + 1}. [${tag}] ${p.path}`,
        `   Change: ${p.change}`,
        `   Why: ${p.why}`,
      ].join('\n');
    }),
    ``,
    'Rule: patches must name files under apps/vscode/ (or docs/sessions/PHASES.md for stage tip).',
    'Forbidden: Live Share, marketplace installs, "update VS Code", generic multi-agent fluff.',
  ].join('\n');

  return { root, version, patches: chosen, report };
}
