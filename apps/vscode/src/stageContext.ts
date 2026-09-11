import * as fs from 'fs';
import * as path from 'path';
import * as vscode from 'vscode';
import { detectWorkspaceMode, resolveProductHome } from './workspaceMode';

export interface StageBrief {
  phaseId: string;
  phaseTitle: string;
  productHome: string;
  tipLine: string;
  extensionVersion: string;
  stackDefaults: string[];
  abilityRollup: string[];
  briefForPrompt: string;
  summaryLine: string;
}

const ABILITY_ROLLUP = [
  'Hive chat/completions + streaming (:8001 → Vulkan :8080)',
  'Multi-agent pipeline (planner → worker → critic)',
  '116+ Hive tools (workspace_*, craft_*, hive_*, voice_*, self_heal_*, omnibrain, world_brain, …)',
  '68 agents + 12 hive core roles (overseer/coder/architect/analyst/memory/governor/router)',
  'Self-heal / promote queue / ability coverage',
  'LoRA + recovery inventory',
  'Workspace IDE context pack (file/git/repo sketch)',
  'Voice Lab surface (:8890) when running',
  'Session phase map in docs/sessions/PHASES.md',
];

function readExtensionVersion(workspaceRoot: string): string {
  // Prefer the *installed* extension package — workspace may be missing or stale.
  try {
    const ext =
      vscode.extensions.getExtension('Unwrenchable.realai-vscode') ||
      vscode.extensions.getExtension('unwrenchable.realai-vscode');
    const ver = ext?.packageJSON?.version;
    if (ver) return String(ver);
    if (ext?.extensionPath) {
      const pkg = JSON.parse(
        fs.readFileSync(path.join(ext.extensionPath, 'package.json'), 'utf8')
      );
      if (pkg?.version) return String(pkg.version);
    }
  } catch {
    /* fall through */
  }
  try {
    const pkg = JSON.parse(
      fs.readFileSync(path.join(workspaceRoot, 'apps', 'vscode', 'package.json'), 'utf8')
    );
    return String(pkg.version || '1.2.7');
  } catch {
    return '1.2.7';
  }
}

function readPhaseTip(workspaceRoot: string): { id: string; title: string; tip: string } {
  const mode = detectWorkspaceMode(workspaceRoot);
  const phasesPath = path.join(workspaceRoot, 'docs', 'sessions', 'PHASES.md');
  try {
    const text = fs.readFileSync(phasesPath, 'utf8');
    const tip =
      (text.match(/\*\*Current tip of product work:\*\*\s*(.+)/)?.[1] || '').trim() ||
      'Phase I - RealAI Ultimate VS Code integration';
    const headings = [...text.matchAll(/^## (Phase [A-Z0-9]+)[^\n]*-\s*([^\n(]+)/gm)];
    const last = headings.length ? headings[headings.length - 1] : null;
    if (last) {
      return { id: last[1].trim(), title: last[2].trim(), tip };
    }
    return { id: 'Phase I', title: 'Ultimate VS Code integration', tip };
  } catch {
    if (mode.hostMode === 'foreign') {
      return {
        id: 'Host',
        title: 'Foreign repo full-stack',
        tip: `Foreign repo mode — full-stack on ${mode.workspaceName}`,
      };
    }
    return {
      id: 'Phase I',
      title: 'Ultimate VS Code integration',
      tip: `RealAI Ultimate extension on ${resolveProductHome(workspaceRoot)}`,
    };
  }
}

export function buildStageBrief(workspaceRoot?: string): StageBrief {
  const folder = vscode.workspace.workspaceFolders?.[0]?.uri.fsPath;
  const root = workspaceRoot || folder || process.cwd();
  const mode = detectWorkspaceMode(root);
  const productHome = mode.productHome;
  const phase = readPhaseTip(root);
  const extensionVersion = readExtensionVersion(root);
  const tipLine = phase.tip
    .replace(/realai-vscode@\d+\.\d+\.\d+/g, `realai-vscode@${extensionVersion}`)
    .replace(/`realai-vscode@[^`]+`/g, `\`realai-vscode@${extensionVersion}\``);

  const stackDefaults =
    mode.hostMode === 'foreign'
      ? [
          `HOST WORKSPACE (foreign): ${mode.workspaceRoot}`,
          `Product home (Hive install): ${productHome}`,
          'Hive API: http://127.0.0.1:8001',
          'Vulkan inference: http://127.0.0.1:8080',
          'Voice Lab (optional): http://127.0.0.1:8890',
          `VS Code extension: realai-vscode@${extensionVersion} (installed; not assumed in this repo)`,
          `Build hints: ${mode.stack.buildHints.slice(0, 4).join(' | ')}`,
        ]
      : [
          `Product home: ${productHome}`,
          'Hive API: http://127.0.0.1:8001',
          'Vulkan inference: http://127.0.0.1:8080',
          'Voice Lab (optional): http://127.0.0.1:8890',
          `VS Code extension: apps/vscode realai-vscode@${extensionVersion}`,
          'Phase map: docs/sessions/PHASES.md',
        ];

  const briefForPrompt = [
    'REALAI STAGE (authoritative product posture):',
    `- ${phase.id}: ${phase.title}`,
    `- tip: ${tipLine}`,
    `- hostMode: ${mode.hostMode}`,
    `- extension: realai-vscode@${extensionVersion}`,
    ...stackDefaults.map((s) => `- ${s}`),
    mode.hostMode === 'foreign'
      ? '- Full-stack authority in the HOST WORKSPACE — explore/learn/edit/build/test/ship this repo. Hive remains the brain at :8001.'
      : '- rolled-up abilities available through this extension / Hive:',
    ...(mode.hostMode === 'product' ? ABILITY_ROLLUP.map((a) => `  • ${a}`) : mode.stack.buildHints.map((a) => `  • ${a}`)),
    '- You are RealAI fully integrated in VS Code (not Copilot/Grok cloud). Prefer Hive tools + concrete repo paths.',
    '- Never claim you cannot access the workspace when WORKSPACE CONTEXT or repo snapshot is present.',
  ].join('\n');

  return {
    phaseId: phase.id,
    phaseTitle: phase.title,
    productHome,
    tipLine,
    extensionVersion,
    stackDefaults,
    abilityRollup: ABILITY_ROLLUP,
    briefForPrompt,
    summaryLine: `${phase.id} · ext ${extensionVersion}${mode.hostMode === 'foreign' ? ' · FOREIGN' : ''}`,
  };
}
