#!/usr/bin/env node
"use strict";
// Шим команды `aipc`: запускает бинарь, скачанный postinstall.
const fs = require("fs");
const path = require("path");
const { spawnSync } = require("child_process");

const { assetName } = require("../platforms");

function main() {
  const name = assetName();
  if (!name) {
    console.error(
      `aipc: no prebuilt binary for ${process.platform}-${process.arch}. ` +
      "Use pip (git+https://github.com/SysikNagibator/AiPC.git) or a binary from Releases."
    );
    process.exit(1);
  }
  const bin = path.join(__dirname, name);
  if (!fs.existsSync(bin)) {
    console.error(
      `aipc: binary not found at ${bin}. Reinstall the package ` +
      "(postinstall downloads it from GitHub Releases)."
    );
    process.exit(1);
  }
  const r = spawnSync(bin, process.argv.slice(2), { stdio: "inherit" });
  process.exit(r.status === null || r.status === undefined ? 1 : r.status);
}

main();
