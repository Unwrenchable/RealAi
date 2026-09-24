'use strict';

const fs = require('fs');
const path = require('path');
const { pathToFileURL } = require('url');

const moduleCache = new Map();

function candidatePaths(fileName) {
  const vault =
    process.env.REALAI_AFC_VAULT ||
    process.env.ATOMIC_FIZZ_VAULT ||
    path.join(
      process.env.USERPROFILE || 'C:\\Users\\tsmit',
      'ATOMIC-FIZZ-CAPS-VAULT-77-WASTELAND-GPS'
    );
  return [
    path.join(__dirname, 'engines_src', fileName),
    path.join(vault, 'scripts', 'realai', fileName),
    path.join(__dirname, fileName),
  ];
}

async function loadRealAiModule(fileName) {
  if (!fileName || typeof fileName !== 'string') {
    throw new Error('RealAI module filename is required.');
  }
  const tried = [];
  for (const absolutePath of candidatePaths(fileName)) {
    tried.push(absolutePath);
    if (!fs.existsSync(absolutePath)) continue;
    const moduleUrl = pathToFileURL(absolutePath).href;
    if (!moduleCache.has(moduleUrl)) {
      moduleCache.set(moduleUrl, import(moduleUrl));
    }
    return moduleCache.get(moduleUrl);
  }
  const err = new Error(
    'RealAI module not found: ' + fileName + '. Tried: ' + tried.join(' | ')
  );
  err.code = 'REALAI_AFC_ENGINE_PARTIAL';
  throw err;
}

module.exports = {
  loadRealAiModule: loadRealAiModule,
  candidatePaths: candidatePaths,
};
