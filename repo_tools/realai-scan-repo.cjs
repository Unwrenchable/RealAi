const fs = require("fs");
const path = require("path");

function safeStat(p) {
  try {
    return fs.statSync(p);
  } catch (e) {
    return null; // skip broken links or missing files
  }
}

function walk(dir) {
  let results = [];

  let entries;
  try {
    entries = fs.readdirSync(dir);
  } catch (e) {
    return results; // skip unreadable directories
  }

  entries.forEach(file => {
    const full = path.join(dir, file);
    const stat = safeStat(full);

    if (!stat) {
      results.push({
        type: "missing",
        path: full
      });
      return;
    }

    if (stat.isDirectory()) {
      results.push({ type: "dir", path: full });
      results = results.concat(walk(full));
    } else {
      results.push({
        type: "file",
        path: full,
        size: stat.size,
        ext: path.extname(full)
      });
    }
  });

  return results;
}

const root = "C:\\RealAI-clean";
const snapshot = walk(root);

fs.writeFileSync(
  "C:\\RealAI-clean\\results\\repo_snapshot.json",
  JSON.stringify(snapshot, null, 2)
);

console.log("Repo snapshot written safely.");
