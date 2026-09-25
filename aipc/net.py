"""Net: веб-поиск с ПК + SSH."""
from __future__ import annotations


def web_search_pc(query: str, limit: int = 5) -> dict:
    try:
        from ddgs import DDGS  # type: ignore  # новый пакет duckduckgo-search
    except ImportError:
        try:
            from duckduckgo_search import DDGS  # type: ignore
        except ImportError as e:
            return {"ok": False, "error": f"нет поиска: {e}. pip install ddgs"}
    try:
        out = []
        with DDGS() as ddgs:
            for r in ddgs.text(query, max_results=limit):
                out.append({"title": r.get("title"), "url": r.get("href"), "body": r.get("body")})
        return {"ok": True, "results": out}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def download_file(url: str, path: str, timeout: int = 120, max_mb: int = 200) -> dict:
    """Скачать файл по URL (без браузера). Если path папка — имя возьмётся из URL."""
    from pathlib import Path
    from urllib.parse import urlparse
    from urllib.request import Request, urlopen

    from .policy import check_path_allowed

    ok, err = check_path_allowed(path)
    if not ok:
        return {"ok": False, "error": err}
    if not url.lower().startswith(("http://", "https://")):
        return {"ok": False, "error": "только http(s) URL"}
    try:
        size = 0
        limit = max_mb * 1024 * 1024
        p = Path(path).expanduser()
        if not p.suffix and (not p.exists() or p.is_dir()):
            name = Path(urlparse(url).path).name or "download.bin"
            p = p / name
        p.parent.mkdir(parents=True, exist_ok=True)
        req = Request(url, headers={"User-Agent": "AiPC-downloader"})
        with urlopen(req, timeout=timeout) as r, p.open("wb") as f:
            while True:
                chunk = r.read(1024 * 256)
                if not chunk:
                    break
                size += len(chunk)
                if size > limit:
                    try:
                        p.unlink()
                    except Exception:
                        pass
                    return {"ok": False, "error": f"файл больше лимита {max_mb} МБ"}
                f.write(chunk)
        return {"ok": True, "path": str(p), "bytes": size}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def ssh_exec(host: str, username: str, cmd: str, key_path: str | None = None, password: str | None = None, port: int = 22, timeout: int = 30) -> dict:
    try:
        import paramiko  # type: ignore
    except ImportError:
        return {"ok": False, "error": "нет paramiko. pip install paramiko"}
    try:
        c = paramiko.SSHClient()
        c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        c.connect(host, port=port, username=username, key_filename=key_path, password=password, timeout=timeout)
        _, stdout, stderr = c.exec_command(cmd, timeout=timeout)
        out = stdout.read().decode("utf-8", errors="replace")
        err = stderr.read().decode("utf-8", errors="replace")
        c.close()
        return {"ok": True, "output": (out + err)[-20000:]}
    except Exception as e:
        return {"ok": False, "error": str(e)}
