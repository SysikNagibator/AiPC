#!/usr/bin/env node
"use strict";
// Шим команды `aipc`: запускает бинарь из Releases.
// Если postinstall был заблокирован менеджером пакетов — докачиваем при
// первом запуске сами (обычный node-код, политики install-скриптов не касаются).
const fs = require("fs");
const { spawnSync } = require("child_process");

const { assetName } = require("../platforms");
const { binaryPath, downloadBinary } = require("../download");

async function main() {
  const name = assetName();
  if (!name) {
    console.error(
      `aipc: no prebuilt binary for ${process.platform}-${process.arch}. ` +
      "Use pip (git+https://github.com/SysikNagibator/AiPC.git) or a binary from Releases."
    );
    process.exit(1);
  }
  let bin = binaryPath();
  if (!bin || !fs.existsSync(bin)) {
    if (process.env.AIPC_SYSIK_SKIP_DOWNLOAD) {
      console.error(
        `aipc: binary not found and download skipped (AIPC_SYSIK_SKIP_DOWNLOAD). ` +
        "Reinstall the package without the flag."
      );
      process.exit(1);
    }
    console.error("aipc: first run — downloading the binary (~60-95 MB), one moment ...");
    try {
      bin = await downloadBinary();
    } catch (e) {
      console.error(`aipc: download failed: ${e.message || e}`);
      process.exit(1);
    }
  }
  const r = spawnSync(bin, process.argv.slice(2), { stdio: "inherit" });
  process.exit(r.status === null || r.status === undefined ? 1 : r.status);
}

main().catch((e) => {
  console.error(e.message || e);
  process.exit(1);
});
