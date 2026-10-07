"use strict";
// Скачивание prebuilt-бинаря из GitHub Releases (общее для install.js и шима).
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

function binaryPath() {
  const name = assetName();
  return name ? path.join(DEST_DIR, name) : null;
}

async function downloadBinary() {
  const name = assetName();
  if (!name) {
    throw new Error(
      `aipc-sysik: no prebuilt binary for ${process.platform}-${process.arch}. ` +
      "Use pip (git+https://github.com/SysikNagibator/AiPC.git) or a binary from Releases."
    );
  }
  if (process.platform === "darwin" && process.arch === "x64") {
    console.warn("aipc-sysik: macOS binary is ARM64 (Apple Silicon); Intel Macs need a build from source.");
  }
  const url = downloadUrl(name);
  const dest = path.join(DEST_DIR, name);
  const tmp = dest + ".part";
  console.log(`aipc-sysik: downloading ${name} ...`);
  fs.mkdirSync(DEST_DIR, { recursive: true });
  const res = await fetch(url);
  await new Promise((resolve, reject) => {
    const out = fs.createWriteStream(tmp, { mode: 0o755 });
    res.pipe(out);
    out.on("finish", resolve);
    out.on("error", reject);
    res.on("error", reject);
  });
  const size = fs.statSync(tmp).size;
  if (size < 10 * 1024 * 1024) {
    fs.unlinkSync(tmp);
    throw new Error(`aipc-sysik: downloaded file too small (${size} bytes) — broken download.`);
  }
  fs.renameSync(tmp, dest);
  if (process.platform !== "win32") {
    fs.chmodSync(dest, 0o755);
  }
  console.log(`aipc-sysik: installed ${dest} (${(size / 1048576).toFixed(1)} MB).`);
  return dest;
}

module.exports = { binaryPath, downloadBinary };
