#!/usr/bin/env node
/**
 * Copy product-root console.html into the extension webview package.
 * Product root is ../.. from apps/vscode.
 */
const fs = require('fs');
const path = require('path');

const vscodeRoot = path.resolve(__dirname, '..');
const productRoot = path.resolve(vscodeRoot, '..', '..');
const src = path.join(productRoot, 'console.html');
const destDir = path.join(vscodeRoot, 'webview');
const dest = path.join(destDir, 'console.html');

if (!fs.existsSync(src)) {
  console.warn(`[sync-webview] skip: missing ${src}`);
  process.exit(0);
}
fs.mkdirSync(destDir, { recursive: true });
fs.copyFileSync(src, dest);
console.log(`[sync-webview] ${src} -> ${dest}`);