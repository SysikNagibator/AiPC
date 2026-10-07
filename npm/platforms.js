"use strict";
// Общая карта: npm-пакет -> ассет GitHub-релиза под текущую ОС.
// При bump версии обновить RELEASE_TAG + имена файлов здесь и в package.json.
const RELEASE_TAG = "v1.1";

const ASSETS = {
  "win32-x64": "AiPC_Win_1.1.exe",
  "darwin-x64": "AiPC_macOS_1.1",
  "darwin-arm64": "AiPC_macOS_1.1",
  "linux-x64": "AiPC_Linux_1.1",
};

function assetName() {
  return ASSETS[`${process.platform}-${process.arch}`] || null;
}

function downloadUrl(name) {
  return `https://github.com/SysikNagibator/AiPC/releases/download/${RELEASE_TAG}/${name}`;
}

module.exports = { RELEASE_TAG, ASSETS, assetName, downloadUrl };
