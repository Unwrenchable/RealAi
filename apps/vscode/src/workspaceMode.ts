import * as fs from 'fs';
import * as path from 'path';
import * as vscode from 'vscode';

export type HostMode = 'product' | 'foreign';

export interface StackHints {
  packageJson?: boolean;
  packageScripts: string[];
  pyproject?: boolean;
  requirementsTxt?: boolean;
  cargoToml?: boolean;
  goMod?: boolean;
  dockerfile?: boolean;
  makefile?: boolean;
  composerJson?: boolean;
  gemfile?: boolean;
  cmakeLists?: boolean;
  languages: string[];
  buildHints: string[];
}

export interface WorkspaceModeInfo {
  hostMode: HostMode;
  workspaceRoot: string;
  workspaceName: string;
  productHome: string;
  isProductHome: boolean;
  stack: StackHints;
}

const DEFAULT_PRODUCT_HOME = 'C:\\RealAI-clean';

function normalizePath(p: string): string {
  try {
    return path.resolve(p).replace(/\//g, '\\').toLowerCase();
  } catch {
    return String(p || '').replace(/\//g, '\\').toLowerCase();
  }
}

/** Discover RealAI product home (Hive install), not the open workspace. */
export function resolveProductHome(workspaceRoot?: string): string {
  const envHome = (process.env.REALAI_HOME || '').trim();
  if (envHome && fs.existsSync(envHome)) return path.resolve(envHome);

  try {
    const cfg = vscode.workspace.getConfiguration('realai').get<string>('productHome');
    if (cfg && fs.existsSync(cfg)) return path.resolve(cfg);
  } catch {
    /* ignore */
  }

  try {
    const ext =
      vscode.extensions.getExtension('Unwrenchable.realai-vscode') ||
      vscode.extensions.getExtension('unwrenchable.realai-vscode');
    if (ext?.extensionPath) {
      const candidate = path.resolve(ext.extensionPath, '..', '..');
      if (looksLikeProductHome(candidate)) return candidate;
    }
  } catch {
    /* ignore */
  }

  if (workspaceRoot && looksLikeProductHome(workspaceRoot)) {
    return path.resolve(workspaceRoot);
  }

  if (fs.existsSync(DEFAULT_PRODUCT_HOME)) return DEFAULT_PRODUCT_HOME;
  return DEFAULT_PRODUCT_HOME;
}

function hasRealaiOrchestrator(root: string): boolean {
  return (
    fs.existsSync(path.join(root, 'realai', 'v3_orchestrator.py')) ||
    fs.existsSync(path.join(root, 'realai', 'orchestration', 'v3_orchestrator.py'))
  );
}

function hasRealaiVscodePkg(root: string): boolean {
  const pkgPath = path.join(root, 'apps', 'vscode', 'package.json');
  try {
    const pkg = JSON.parse(fs.readFileSync(pkgPath, 'utf8'));
    return String(pkg?.name || '') === 'realai-vscode';
  } catch {
    return false;
  }
}

export function looksLikeProductHome(root: string): boolean {
  const n = normalizePath(root);
  if (n.includes('realai-clean')) return true;
  return hasRealaiOrchestrator(root) && hasRealaiVscodePkg(root);
}

export function detectHostMode(root: string): HostMode {
  return looksLikeProductHome(root) ? 'product' : 'foreign';
}
export function detectStackHints(root: string): StackHints {
  const exists = (rel: string) => fs.existsSync(path.join(root, rel));
  const packageJson = exists('package.json');
  let packageScripts: string[] = [];
  if (packageJson) {
    try {
      const pkg = JSON.parse(fs.readFileSync(path.join(root, 'package.json'), 'utf8'));
      packageScripts = Object.keys(pkg?.scripts || {}).slice(0, 24);
    } catch {
      packageScripts = [];
    }
  }
  const pyproject = exists('pyproject.toml');
  const requirementsTxt = exists('requirements.txt') || exists('requirements-dev.txt');
  const cargoToml = exists('Cargo.toml');
  const goMod = exists('go.mod');
  const dockerfile = exists('Dockerfile') || exists('docker-compose.yml') || exists('compose.yml');
  const makefile = exists('Makefile') || exists('makefile');
  const composerJson = exists('composer.json');
  const gemfile = exists('Gemfile');
  const cmakeLists = exists('CMakeLists.txt');

  const languages: string[] = [];
  if (packageJson) languages.push('javascript/typescript');
  if (pyproject || requirementsTxt || exists('setup.py')) languages.push('python');
  if (cargoToml) languages.push('rust');
  if (goMod) languages.push('go');
  if (composerJson) languages.push('php');
  if (gemfile) languages.push('ruby');
  if (cmakeLists || exists('meson.build')) languages.push('c/c++');
  if (exists('build.gradle') || exists('build.gradle.kts') || exists('pom.xml')) languages.push('jvm');

  const buildHints: string[] = [];
  if (packageScripts.length) {
    const interesting = packageScripts.filter((s) =>
      /^(build|test|start|dev|lint|typecheck|compile|serve|watch)/i.test(s)
    );
    const shown = (interesting.length ? interesting : packageScripts.slice(0, 8)).join(', ');
    buildHints.push('package scripts: ' + shown);
  }
  if (pyproject) buildHints.push('Python project (pyproject.toml)');
  else if (requirementsTxt) buildHints.push('Python requirements.txt present');
  if (cargoToml) buildHints.push('Rust crate - cargo build / cargo test');
  if (goMod) buildHints.push('Go module - go build ./...');
  if (dockerfile) buildHints.push('Containerized - Dockerfile/compose present');
  if (makefile) buildHints.push('Make targets available');
  if (composerJson) buildHints.push('PHP Composer project');
  if (gemfile) buildHints.push('Ruby Bundler project');
  if (cmakeLists) buildHints.push('CMake project');
  if (!buildHints.length) buildHints.push('No standard build manifest detected - explore tree first');

  return {
    packageJson,
    packageScripts,
    pyproject,
    requirementsTxt,
    cargoToml,
    goMod,
    dockerfile,
    makefile,
    composerJson,
    gemfile,
    cmakeLists,
    languages,
    buildHints,
  };
}

export function detectWorkspaceMode(workspaceRoot?: string): WorkspaceModeInfo {
  const folder = vscode.workspace.workspaceFolders?.[0];
  const root = workspaceRoot || folder?.uri.fsPath || process.cwd();
  const workspaceName = folder?.name || path.basename(root);
  const productHome = resolveProductHome(root);
  const hostMode = detectHostMode(root);
  return {
    hostMode,
    workspaceRoot: path.resolve(root),
    workspaceName,
    productHome,
    isProductHome: hostMode === 'product',
    stack: detectStackHints(root),
  };
}

export function genericProjectCandidates(): string[] {
  return [
    "README.md",
    "README.rst",
    "README.txt",
    "package.json",
    "pyproject.toml",
    "requirements.txt",
    "setup.py",
    "Cargo.toml",
    "go.mod",
    "Makefile",
    "makefile",
    "Dockerfile",
    "compose.yml",
    "CMakeLists.txt",
    "composer.json",
    "Gemfile",
    "build.gradle",
    "pom.xml",
    "tsconfig.json",
    "src/",
    "app/",
    "apps/",
    "lib/",
    "cmd/",
    "internal/",
    "tests/",
    "test/",
  ];
}

export function productProjectCandidates(): string[] {
  const av = "apps/vscode";
  return [
    "REALAI_3.0.md",
    "QUICKSTART_LOCAL.md",
    "How to run RealAI.txt",
    "ABILITIES.md",
    "ANY_REPO.md",
    "console.html",
    av + "/package.json",
    av + "/src/extension.ts",
    av + "/src/chatPanel.ts",
    av + "/src/contextPack.ts",
    av + "/src/realaiClient.ts",
    "realai/orchestration/v3_orchestrator.py",
    "realai/v3_orchestrator.py",
  ];
}
