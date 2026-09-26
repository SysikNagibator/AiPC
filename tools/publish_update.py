"""Публикация указателя версии для aipc update (fallback когда GitHub-релизы недоступны).

Использование:
  1. Залей zip вручную (или скриптом) на зеркало, получи URL.
  2. python tools/publish_update.py --version 1.0.4.14 --url https://files.catbox.moe/XXX.zip --sha256 ABC...
Требует env GITHUB_TOKEN (classic, scope gist).
"""
from __future__ import annotations

import json
import os
import sys
import urllib.request

GIST_ID = "e346d2345f9b290a3896868c6351ca0c"


def main(argv: list[str]) -> int:
    args = {"version": None, "url": None, "sha256": "", "notes": ""}
    i = 0
    while i < len(argv):
        if argv[i].startswith("--") and i + 1 < len(argv):
            args[argv[i][2:]] = argv[i + 1]
            i += 2
        else:
            i += 1
    if not args["version"] or not args["url"]:
        print("Нужно: --version X --url https://... [--sha256 ...] [--notes ...]")
        return 1
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN", "")
    if not token:
        print("Нужен env GITHUB_TOKEN (classic, scope gist)")
        return 1
    payload = {"files": {"aipc-latest.json": {"content": json.dumps({
        "version": args["version"], "exe_url": args["url"],
        "sha256": args["sha256"], "notes": args["notes"]}, ensure_ascii=False)}}}
    req = urllib.request.Request(
        f"https://api.github.com/gists/{GIST_ID}",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"},
        method="PATCH",
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        print("gist updated:", r.status)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
