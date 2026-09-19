#!/usr/bin/env node

const fs = require("fs");
const path = require("path");
const loadPlugins = require("./core/plugins");

// Load all plugins
const plugins = loadPlugins();

// Parse command + args
const cmd = process.argv[2];
const args = process.argv.slice(3);

// 1. Try built‑in commands
const builtinPath = path.join(__dirname, "commands", `${cmd}.js`);
if (fs.existsSync(builtinPath)) {
  require(builtinPath)(args);
  process.exit(0);
}

// 2. Try plugins
for (const plugin of plugins) {
  if (plugin.commands.includes(cmd)) {
    plugin.run(cmd, args);
    process.exit(0);
  }
}

// 3. Fallback to help
require("./commands/help")();
