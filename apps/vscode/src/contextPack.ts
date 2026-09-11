import * as vscode from 'vscode';
import * as path from 'path';
import { execFile } from 'child_process';
import { promisify } from 'util';
import * as fs from 'fs';
import { buildStageBrief } from './stageContext';
import {
  detectWorkspaceMode,
  genericProjectCandidates,
  productProjectCandidates,
  type HostMode,
} from './workspaceMode';

const execFileAsync = promisify(execFile);

export interface ContextSnapshot {
  workspaceRoot: string;
  workspaceName: string;
  hostMode: HostMode;
  productHome: string;
  foreignRepo: boolean;
  buildHints: string[];
  activeFile?: string;
  languageId?: string;
  cursorLine?: number;
  cursorCol?: number;
  selectionText?: string;
  selectionLines?: string;
  openFiles: string[];
  gitBranch?: string;
  gitDirty?: boolean;
  gitStatusShort?: string;
  projectHints: string[];
  treeSketch: string[];
  extensionFacts: string[];
  activeExcerpt?: string;
  summaryLine: string;
  /** Short rules for role=system (small models often ignore long system prompts) */
  systemPrompt: string;
  /** Compact facts block to prepend onto the user turn */
  userContextBlock: string;
}

const IGNORE_DIR = new Set([
  'node_modules',
  '.git',
  'dist',
  'out',
  'build',
  '.venv',
  'venv',
  '__pycache__',
  '.next',
  'coverage',
  '.turbo',
  'RealAI_Recovery_SAFE',
  'from_recycle_bin',
]);

function rel(root: string, filePath: string): string {
  const r = path.relative(root, filePath);
  return r && !r.startsWith('..') ? r.replace(/\\/g, '/') : filePath.replace(/\\/g, '/');
}

function truncate(text: string, max: number): string {
  if (text.length <= max) return text;
  return text.slice(0, max) + `\n… [truncated ${text.length - max} chars]`;
}

async function gitInfo(root: string): Promise<{ branch?: string; dirty?: boolean; short?: string }> {
  try {
    const { stdout: branchOut } = await execFileAsync(
      'git',
      ['-C', root, 'rev-parse', '--abbrev-ref', 'HEAD'],
      { timeout: 2500, windowsHide: true }
    );
    const branch = branchOut.trim();
    const { stdout: statusOut } = await execFileAsync(
      'git',
      ['-C', root, 'status', '--porcelain', '-b'],
      { timeout: 2500, windowsHide: true }
    );
    const lines = statusOut.split(/\r?\n/).filter(Boolean);
    const dirty = lines.some((l) => !l.startsWith('##'));
    const short = lines.slice(0, 12).join('\n');
    return { branch, dirty, short };
  } catch {
    return {};
  }
}

function listTreeSketch(root: string, maxEntries = 36): string[] {
  const out: string[] = [];
  const walk = (dir: string, depth: number) => {
    if (out.length >= maxEntries || depth > 2) return;
    let entries: fs.Dirent[];
    try {
      entries = fs.readdirSync(dir, { withFileTypes: true });
    } catch {
      return;
    }
    entries.sort((a, b) => a.name.localeCompare(b.name));
    for (const ent of entries) {
      if (out.length >= maxEntries) break;
      if (ent.name.startsWith('.') && ent.name !== '.grok' && ent.name !== '.github') continue;
      if (IGNORE_DIR.has(ent.name)) continue;
      const full = path.join(dir, ent.name);
      const label = rel(root, full) + (ent.isDirectory() ? '/' : '');
      out.push(label);
      if (ent.isDirectory() && depth < 2) walk(full, depth + 1);
    }
  };
  walk(root, 0);
  return out;
}

function projectHints(root: string, hostMode: HostMode): string[] {
  const candidates = [
    ...genericProjectCandidates(),
    ...(hostMode === 'product' ? productProjectCandidates() : []),
  ];
  const seen = new Set<string>();
  const out: string[] = [];
  for (const p of candidates) {
    if (seen.has(p)) continue;
    seen.add(p);
    const full = path.join(root, p.replace(/\/$/, ''));
    try {
      if (fs.existsSync(full)) out.push(p);
    } catch {
      /* ignore */
    }
  }
  return out;
}

function extensionFacts(
  root: string,
  hostMode: HostMode,
  productHome: string
): string[] {
  const facts: string[] = [];
  const cfgBase =
    vscode.workspace.getConfiguration('realai').get<string>('baseUrl') ||
    'http://127.0.0.1:8001';

  if (hostMode === 'foreign') {
    facts.push(
      'Host mode: FOREIGN REPO - this workspace is the target project, not RealAI product home'
    );
    facts.push(`RealAI product home (Hive install): ${productHome}`);
    facts.push(`Hive brain (remote to this repo): ${cfgBase}`);
    facts.push(
      'Do NOT assume apps/vscode or realai/ layout exists in THIS workspace - work against the host repo tree'
    );
    facts.push(
      'Full-stack authority in this workspace: explore, learn, plan, edit, build, test, debug, ship'
    );
    return facts;
  }

  const pkgPath = path.join(root, 'apps', 'vscode', 'package.json');
  try {
    const pkg = JSON.parse(fs.readFileSync(pkgPath, 'utf8'));
    facts.push(`VS Code extension package: apps/vscode (name=${pkg.name}, version=${pkg.version}, publisher=${pkg.publisher})`);
    facts.push(`Extension entry: ${pkg.main || './out/extension.js'}`);
    facts.push(`Default settings: baseUrl=${pkg?.contributes?.configuration?.properties?.['realai.baseUrl']?.default || 'http://127.0.0.1:8001'}, model=${pkg?.contributes?.configuration?.properties?.['realai.model']?.default || 'realai-hive'}`);
  } catch {
    facts.push('VS Code extension lives under apps/vscode (package.json unreadable)');
  }
  const srcDir = path.join(root, 'apps', 'vscode', 'src');
  try {
    const srcFiles = fs
      .readdirSync(srcDir)
      .filter((f) => f.endsWith('.ts'))
      .sort();
    if (srcFiles.length) facts.push(`Extension TypeScript sources: ${srcFiles.map((f) => 'apps/vscode/src/' + f).join(', ')}`);
  } catch {
    /* ignore */
  }
  facts.push(`Hive API default: ${cfgBase} / Vulkan inference: http://127.0.0.1:8080`);
  facts.push('Stack start: realai-stack (or python -m realai stack)');
  facts.push(`Product home: ${productHome}`);
  return facts;
}

function activeExcerpt(doc: vscode.TextDocument, line: number, radius = 35, maxChars = 2800): string {
  const start = Math.max(0, line - radius);
  const end = Math.min(doc.lineCount, line + radius + 1);
  const chunk = doc.getText(new vscode.Range(start, 0, end, 0));
  return truncate(chunk, maxChars);
}

export async function buildContextSnapshot(): Promise<ContextSnapshot> {
  const folder = vscode.workspace.workspaceFolders?.[0];
  const workspaceRoot = folder?.uri.fsPath || process.cwd();
  const workspaceName = folder?.name || path.basename(workspaceRoot);
  const mode = detectWorkspaceMode(workspaceRoot);
  const hostMode = mode.hostMode;
  const productHome = mode.productHome;
  const foreignRepo = hostMode === 'foreign';
  const buildHints = mode.stack.buildHints;

  const editor = vscode.window.activeTextEditor;
  const openFiles = vscode.window.visibleTextEditors
    .map((e) => rel(workspaceRoot, e.document.uri.fsPath))
    .filter((v, i, a) => a.indexOf(v) === i)
    .slice(0, 8);

  let activeFile: string | undefined;
  let languageId: string | undefined;
  let cursorLine: number | undefined;
  let cursorCol: number | undefined;
  let selectionText: string | undefined;
  let selectionLines: string | undefined;
  let activeExcerptText: string | undefined;

  if (editor) {
    activeFile = rel(workspaceRoot, editor.document.uri.fsPath);
    languageId = editor.document.languageId;
    cursorLine = editor.selection.active.line + 1;
    cursorCol = editor.selection.active.character + 1;
    const sel = editor.document.getText(editor.selection);
    if (sel.trim()) {
      selectionText = truncate(sel, 2200);
      selectionLines = `${editor.selection.start.line + 1}-${editor.selection.end.line + 1}`;
    }
    activeExcerptText = activeExcerpt(editor.document, editor.selection.active.line);
  }

  const git = await gitInfo(workspaceRoot);
  const hints = projectHints(workspaceRoot, hostMode);
  const treeSketch = listTreeSketch(workspaceRoot);
  const extFacts = extensionFacts(workspaceRoot, hostMode, productHome);
  const stage = buildStageBrief(workspaceRoot);

  const summaryParts = [
    stage.summaryLine,
    foreignRepo ? `FOREIGN:${workspaceName}` : workspaceName,
    git.branch ? `git:${git.branch}${git.dirty ? '*' : ''}` : undefined,
    activeFile ? `${activeFile}:${cursorLine || 1}` : 'no-file',
  ].filter(Boolean);
  const summaryLine = summaryParts.join(' · ');

  const systemPrompt = foreignRepo
    ? [
        'You are RealAI Ultimate inside VS Code - local Hive brain, not Copilot/Grok cloud.',
        `Host mode: FOREIGN REPO. Workspace is ${workspaceName} at ${workspaceRoot}.`,
        `RealAI product home remains ${productHome} / Hive :8001.`,
        'You have full-stack authority in THIS repo: explore, learn, plan, edit, build, test, debug, ship.',
        'Do not assume RealAI-clean layout (no apps/vscode / realai/ required here).',
        'Use WORKSPACE CONTEXT + REALAI STAGE in the user message as authoritative facts.',
        'Be concrete: cite real paths in THIS workspace, Hive endpoints, tools, and next steps.',
      ].join(' ')
    : [
        'You are RealAI Ultimate inside VS Code - fully integrated local RealAI (Hive), not Copilot/Grok cloud.',
        'Use WORKSPACE CONTEXT + REALAI STAGE in the user message as authoritative facts.',
        'Be concrete: cite real paths, Hive endpoints, tools, and next steps. Never give generic product-speak filler.',
        'If a Hive tool result or repo snapshot is present, use it. Never claim you cannot access the workspace in that case.',
        'You can suggest slash flows: /phase /repo /tools /agents /multi /heal /caps.',
      ].join(' ');

  const userContextBlock = [
    stage.briefForPrompt,
    '',
    'WORKSPACE CONTEXT (authoritative):',
    `- hostMode: ${hostMode}`,
    `- foreignRepo: ${foreignRepo}`,
    `- productHome: ${productHome}`,
    `- root: ${workspaceRoot}`,
    `- name: ${workspaceName}`,
    foreignRepo
      ? `- NOTE: Host mode FOREIGN REPO. Workspace is ${workspaceName} at ${workspaceRoot}. RealAI product home remains ${productHome} / Hive :8001. Full-stack authority in THIS repo - do not assume RealAI-clean layout.`
      : '',
    git.branch
      ? `- git: ${git.branch}${git.dirty ? ' (dirty)' : ' (clean)'}`
      : '- git: unavailable',
    git.short ? `- git status:\n${git.short}` : '',
    activeFile
      ? `- active file: ${activeFile} (${languageId || 'text'}) @ L${cursorLine}:C${cursorCol}`
      : '- active file: none',
    openFiles.length ? `- visible editors: ${openFiles.join(', ')}` : '',
    buildHints.length ? `- build hints: ${buildHints.join(' | ')}` : '',
    mode.stack.languages.length
      ? `- detected languages: ${mode.stack.languages.join(', ')}`
      : '',
    ...extFacts.map((f) => `- ${f}`),
    hints.length ? `- key files present: ${hints.join(', ')}` : '',
    treeSketch.length
      ? `- repo sketch:\n${treeSketch
          .slice(0, 28)
          .map((t) => `  - ${t}`)
          .join('\n')}`
      : '',
    selectionText
      ? `- selection L${selectionLines}:\n\`\`\`${languageId || ''}\n${selectionText}\n\`\`\``
      : '',
    !selectionText && activeExcerptText
      ? `- active excerpt:\n\`\`\`${languageId || ''}\n${activeExcerptText}\n\`\`\``
      : '',
  ]
    .filter((line) => line !== '')
    .join('\n');

  return {
    workspaceRoot,
    workspaceName,
    hostMode,
    productHome,
    foreignRepo,
    buildHints,
    activeFile,
    languageId,
    cursorLine,
    cursorCol,
    selectionText,
    selectionLines,
    openFiles,
    gitBranch: git.branch,
    gitDirty: git.dirty,
    gitStatusShort: git.short,
    projectHints: hints,
    treeSketch,
    extensionFacts: extFacts,
    activeExcerpt: activeExcerptText,
    summaryLine,
    systemPrompt,
    userContextBlock,
  };
}
