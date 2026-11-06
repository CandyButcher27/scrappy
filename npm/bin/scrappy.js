#!/usr/bin/env node
// scrappy is a Python package; this runs the matching PyPI release through uvx, installing uv first if needed.
const { spawnSync } = require("node:child_process");
const { existsSync } = require("node:fs");
const { homedir } = require("node:os");
const { join } = require("node:path");
const { version } = require("../package.json");

const win = process.platform === "win32";
const localUvx = join(homedir(), ".local", "bin", win ? "uvx.exe" : "uvx");

function findUvx() {
  if (spawnSync("uvx", ["--version"], { stdio: "ignore" }).status === 0) return "uvx";
  return existsSync(localUvx) ? localUvx : null;
}

let uvx = findUvx();
if (!uvx) {
  console.error("scrappy-agent: uv not found, installing it from https://astral.sh/uv");
  // The installer's output goes to stderr so stdout stays clean when running as an MCP server.
  const io = { stdio: ["ignore", 2, 2] };
  if (win) {
    spawnSync("powershell", ["-NoProfile", "-ExecutionPolicy", "ByPass", "-Command", "irm https://astral.sh/uv/install.ps1 | iex"], io);
  } else {
    spawnSync("sh", ["-c", "curl -LsSf https://astral.sh/uv/install.sh | sh"], io);
  }
  uvx = findUvx();
  if (!uvx) {
    console.error("scrappy-agent: could not install uv. Install it manually: https://docs.astral.sh/uv/getting-started/installation/");
    process.exit(1);
  }
}

const source = process.env.SCRAPPY_FROM || `scrappy-agent==${version}`;
const run = spawnSync(uvx, ["--from", source, "scrappy", ...process.argv.slice(2)], { stdio: "inherit" });
process.exit(run.status ?? 1);
