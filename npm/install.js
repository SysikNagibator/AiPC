"use strict";
// postinstall: скачать готовый бинарь AiPC под текущую ОС из GitHub Releases.
// Пропуск (офлайн/зеркала): AIPC_SYSIK_SKIP_DOWNLOAD=1
const fs = require("fs");
const https = require("https");
const path = require("path");

const { assetName, downloadUrl } = require("./platforms");

const DEST_DIR = path.join(__dirname, "bin");

function fetch(url, redirects = 5) {
  return new Promise((resolve, reject) => {
    https.get(url, { headers: { "User-Agent": "aipc-sysik-installer" } }, (res) => {
      if (res.statusCode >= 300 && res.statusCode < 400 && res.headers.location) {
        if (redirects <= 0) return reject(new Error("too many redirects"));
        res.resume();
        return resolve(fetch(res.headers.location, redirects - 1));
      }
      if (res.statusCode !== 200) {
        res.resume();
        return reject(new Error(`download failed: HTTP ${res.statusCode} (${url})`));
      }
      resolve(res);
    }).on("error", reject);
  });
}

async function main() {
  if (process.env.AIPC_SYSIK_SKIP_DOWNLOAD) {
    console.log("aipc-sysik: download skipped (AIPC_SYSIK_SKIP_DOWNLOAD).");
    return;
  }
  const name = assetName();
  if (!name) {
    throw new Error(
      `aipc-sysik: no prebuilt binary for ${process.platform}-${process.arch}. ` +
      "Use pip (git+https://github.com/SysikNagibator/AiPC.git) or a binary from Releases."
    );
  }
  if (process.platform === "darwin" && process.arch === "x64") {
    console.warn("aipc-sysik: macOS binary is ARM64 (Apple Silicon); Intel Macs need Rosetta-free build from source.");
  }
  const url = downloadUrl(name);
  const dest = path.join(DEST_DIR, name);
  console.log(`aipc-sysik: downloading ${name} ...`);
  fs.mkdirSync(DEST_DIR, { recursive: true });
  const res = await fetch(url);
  await new Promise((resolve, reject) => {
    const out = fs.createWriteStream(dest, { mode: 0o755 });
    res.pipe(out);
    out.on("finish", resolve);
    out.on("error", reject);
    res.on("error", reject);
  });
  if (process.platform !== "win32") {
    fs.chmodSync(dest, 0o755);
  }
  const size = fs.statSync(dest).size;
  if (size < 10 * 1024 * 1024) {
    fs.unlinkSync(dest);
    throw new Error(`aipc-sysik: downloaded file too small (${size} bytes) — broken download.`);
  }
  console.log(`aipc-sysik: installed ${dest} (${(size / 1048576).toFixed(1)} MB). Run: aipc`);
}

main().catch((e) => {
  console.error(e.message || e);
  process.exit(1);
});
