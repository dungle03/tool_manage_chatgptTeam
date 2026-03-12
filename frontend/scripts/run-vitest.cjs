const { realpathSync } = require("node:fs");
const { resolve } = require("node:path");
const { spawnSync } = require("node:child_process");

const projectPath = resolve(__dirname, "..");
const realProjectPath = realpathSync(projectPath);
const vitestEntry = resolve(realProjectPath, "node_modules", "vitest", "vitest.mjs");
const args = [vitestEntry, "run", ...process.argv.slice(2)];

const result = spawnSync(process.execPath, args, {
  cwd: realProjectPath,
  stdio: "inherit",
  env: {
    ...process.env,
    INIT_CWD: realProjectPath,
  },
});

if (result.error) {
  throw result.error;
}

process.exit(result.status ?? 1);
