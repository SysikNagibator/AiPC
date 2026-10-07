"use strict";
// postinstall: предзагрузка бинаря (если npm заблокировал скрипты,
// шим докачает сам при первом запуске `aipc`).
// Пропуск (офлайн/зеркала): AIPC_SYSIK_SKIP_DOWNLOAD=1
const { downloadBinary } = require("./download");

async function main() {
  if (process.env.AIPC_SYSIK_SKIP_DOWNLOAD) {
    console.log("aipc-sysik: download skipped (AIPC_SYSIK_SKIP_DOWNLOAD).");
    return;
  }
  try {
    await downloadBinary();
    console.log("aipc-sysik: ready. Run: aipc");
  } catch (e) {
    // Не валим установку: шим попробует ещё раз при первом запуске.
    console.warn(`aipc-sysik: postinstall download failed: ${e.message || e}`);
  }
}

main();
