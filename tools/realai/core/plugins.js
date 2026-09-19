const fs = require("fs");
const path = require("path");

module.exports = function loadPlugins() {
  const pluginDir = path.join(__dirname, "..", "plugins");
  const files = fs.readdirSync(pluginDir);

  return files.map(file => {
    const plugin = require(path.join(pluginDir, file));
    return plugin;
  });
};
