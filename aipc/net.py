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


def download_file(url: str, path: str, timeout: int = 120, max_mb: int = 0) -> dict:
    """Скачать файл по URL (без браузера). max_mb=0 — без лимита, стрим на диск."""
    from pathlib import Path
    from urllib.parse import urlparse
    from urllib.request import Request, urlopen

    from .os_ops import check_free_space
    from .policy import check_path_allowed

    ok, err = check_path_allowed(path)
    if not ok:
        return {"ok": False, "error": err}
    if not url.lower().startswith(("http://", "https://")):
        return {"ok": False, "error": "только http(s) URL"}
    try:
        size = 0
        limit = max_mb * 1024 * 1024 if max_mb and max_mb > 0 else 0
        p = Path(path).expanduser()
        if not p.suffix and (not p.exists() or p.is_dir()):
            name = Path(urlparse(url).path).name or "download.bin"
            p = p / name
        p.parent.mkdir(parents=True, exist_ok=True)
        ok, err = check_free_space(str(p))
        if not ok:
            return {"ok": False, "reason": "no_space", "error": err}
        req = Request(url, headers={"User-Agent": "AiPC-downloader"})
        with urlopen(req, timeout=timeout) as r, p.open("wb") as f:
            while True:
                chunk = r.read(1024 * 256)
                if not chunk:
                    break
                size += len(chunk)
                if limit and size > limit:
                    try:
                        p.unlink()
                    except Exception:
                        pass
                    return {"ok": False, "reason": "too_big", "error": f"файл больше лимита {max_mb} МБ"}
                f.write(chunk)
        return {"ok": True, "path": str(p), "bytes": size}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def _ssh_connect(host: str, username: str, key_path=None, password=None, port: int = 22, timeout: int = 30):
    import paramiko  # type: ignore

    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    c.connect(host, port=port, username=username, key_filename=key_path, password=password, timeout=timeout)
    return c


def ssh_exec(host: str, username: str, cmd: str, key_path: str | None = None, password: str | None = None, port: int = 22, timeout: int = 30) -> dict:
    try:
        import paramiko  # type: ignore  # noqa (проверка зависимости)
    except ImportError:
        return {"ok": False, "reason": "missing_dep", "error": "нет paramiko. pip install paramiko"}
    try:
        c = _ssh_connect(host, username, key_path, password, port, timeout)
        try:
            _, stdout, stderr = c.exec_command(cmd, timeout=timeout)
            out = stdout.read().decode("utf-8", errors="replace")
            err = stderr.read().decode("utf-8", errors="replace")
        finally:
            c.close()
        return {"ok": True, "output": (out + err)[-20000:]}
    except Exception as e:
        return {"ok": False, "reason": "error", "error": str(e)[:500]}


def _ssh_saved(host: str) -> tuple:
    """key_path, port из конфига. Безопасно для кривого port."""
    from .config import load_config

    saved = (load_config().get("ssh_hosts") or {}).get(host, {})
    try:
        port = int(saved.get("port", 22))
    except (TypeError, ValueError):
        port = 22
    return saved.get("key_path"), port


def ssh_sftp_get(host: str, username: str, remote: str, local: str, timeout: int = 60) -> dict:
    """Забрать файл по SSH (remote -> local)."""
    from pathlib import Path

    from .policy import check_path_allowed

    ok, err = check_path_allowed(local)
    if not ok:
        return {"ok": False, "reason": "denied", "error": err}
    try:
        import paramiko  # type: ignore  # noqa
    except ImportError:
        return {"ok": False, "reason": "missing_dep", "error": "нет paramiko. pip install paramiko"}
    try:
        key_path, port = _ssh_saved(host)
        c = _ssh_connect(host, username, key_path, None, port, timeout)
        try:
            sftp = c.open_sftp()
            try:
                remote_size = 0
                try:
                    remote_size = sftp.stat(remote).st_size or 0
                except Exception:
                    pass
                p = Path(local).expanduser()
                if not p.suffix and (not p.exists() or p.is_dir()):
                    p = p / Path(remote).name
                p.parent.mkdir(parents=True, exist_ok=True)
                from .os_ops import check_free_space

                ok, err = check_free_space(str(p), remote_size)
                if not ok:
                    return {"ok": False, "reason": "no_space", "error": err}
                sftp.get(remote, str(p))
            finally:
                try:
                    sftp.close()
                except Exception:
                    pass
        finally:
            c.close()
        return {"ok": True, "remote": remote, "local": str(p), "bytes": p.stat().st_size}
    except FileNotFoundError:
        return {"ok": False, "reason": "not_found", "error": f"нет файла на сервере: {remote}"}
    except Exception as e:
        return {"ok": False, "reason": "error", "error": str(e)[:500]}


def ssh_sftp_put(host: str, username: str, local: str, remote: str, timeout: int = 60) -> dict:
    """Положить файл по SSH (local -> remote)."""
    from pathlib import Path

    try:
        import paramiko  # type: ignore  # noqa
    except ImportError:
        return {"ok": False, "reason": "missing_dep", "error": "нет paramiko. pip install paramiko"}
    try:
        p = Path(local).expanduser()
        if not p.is_file():
            return {"ok": False, "reason": "not_found", "error": f"нет локального файла: {local}"}
        key_path, port = _ssh_saved(host)
        c = _ssh_connect(host, username, key_path, None, port, timeout)
        try:
            sftp = c.open_sftp()
            try:
                sftp.put(str(p), remote)
            finally:
                try:
                    sftp.close()
                except Exception:
                    pass
        finally:
            c.close()
        return {"ok": True, "local": str(p), "remote": remote, "bytes": p.stat().st_size}
    except Exception as e:
        return {"ok": False, "reason": "error", "error": str(e)[:500]}
