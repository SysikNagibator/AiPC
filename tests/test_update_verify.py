"""R5: SHA256-пин в self_update — подмена и отсутствие сумм блокируются."""
import hashlib
import io
import json

from aipc import maintenance as M


def _resp(data: bytes):
    class _R:
        def __init__(self, d):
            self._d = d

        def read(self, n=-1):
            if n is None or n < 0:
                out, self._d = self._d, b""
                return out
            out, self._d = self._d[:n], self._d[n:]
            return out

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    return _R(data)


def test_sha256_file(tmp_path):
    p = tmp_path / "a.bin"
    p.write_bytes(b"abc" * 1000)
    assert M._sha256_file(p) == hashlib.sha256(b"abc" * 1000).hexdigest()


def test_find_hash_certutil_format():
    hex64 = "0123456789abcdef" * 4
    text = ("SHA256 file C:\\d\\AiPC_Win_1.2.exe:\n" + hex64 + "\n"
            + "CertUtil: done.\n")
    assert M._find_expected_hash(text, "AiPC_Win_1.2.exe") == hex64


def test_find_hash_github_format():
    text = "deadbeef" * 8 + "  AiPC_Win_1.2.exe\n" + "00" * 32 + "  other.exe\n"
    assert M._find_expected_hash(text, "AiPC_Win_1.2.exe") == ("deadbeef" * 8)
    assert M._find_expected_hash(text, "missing.exe") == ""
    assert M._find_expected_hash("", "x.exe") == ""


def _fake_release(monkeypatch, exe_bytes: bytes, sums_text: str | None):
    rel = {"tag_name": "v9.9.9", "html_url": "https://x/y", "body": "",
           "assets": [{"name": "AiPC_Win_9.9.9.exe",
                       "browser_download_url": "https://x/e.exe", "size": 1}]}
    if sums_text is not None:
        rel["assets"].append({"name": "SHA256SUMS.txt",
                              "browser_download_url": "https://x/s.txt", "size": 1})

    def _fake_urlopen(req, timeout=None):
        url = req.full_url if hasattr(req, "full_url") else str(req)
        if "api.github.com" in url:
            return _resp(json.dumps(rel).encode())
        if url.endswith("s.txt"):
            return _resp(sums_text.encode())
        return _resp(exe_bytes)

    monkeypatch.setattr(M, "urlopen", _fake_urlopen)
    monkeypatch.setattr(M, "check_update",
                        lambda repo=M.UPDATE_REPO: {
                            "ok": True, "update": True, "current": "1.1",
                            "latest": "v9.9.9", "url": "https://x/y",
                            "exe_url": "https://x/e.exe",
                            "exe_name": "AiPC_Win_9.9.9.exe",
                            "sums_url": ("https://x/s.txt"
                                         if sums_text is not None else None)})


def test_no_sums_aborts(monkeypatch, capsys):
    _fake_release(monkeypatch, b"MZ" + b"\x00" * 100, None)
    assert M.self_update() == 1
    assert "SHA256SUMS" in capsys.readouterr().out


def test_per_os_sums_name(monkeypatch):
    import json

    rel = {"tag_name": "v9.9.9", "html_url": "https://x/y", "body": "",
           "assets": [
               {"name": "AiPC_Win_9.9.9.exe",
                "browser_download_url": "https://x/e.exe", "size": 1},
               {"name": "SHA256SUMS-windows-latest.txt",
                "browser_download_url": "https://x/s.txt", "size": 1},
           ]}

    class _R:
        def __init__(self, d):
            self._d = d

        def read(self, n=-1):
            out, self._d = (self._d, b"") if n is None or n < 0 else \
                (self._d[:n], self._d[n:])
            return out

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    def _fake_urlopen(req, timeout=None):
        return _R(json.dumps(rel).encode())

    monkeypatch.setattr(M, "urlopen", _fake_urlopen)
    info = M.check_update()
    assert info["sums_url"] == "https://x/s.txt"


def test_hash_mismatch_aborts(monkeypatch, capsys):
    sums = "00" * 32 + "  AiPC_Win_9.9.9.exe\n"
    _fake_release(monkeypatch, b"MZ" + b"\x11" * 200, sums)
    assert M.self_update() == 1
    out = capsys.readouterr().out
    assert "НЕ СОВПАЛ" in out


def test_hash_match_proceeds(monkeypatch, capsys):
    body = b"MZ" + b"\x22" * 200
    sums = hashlib.sha256(body).hexdigest() + "  AiPC_Win_9.9.9.exe\n"
    _fake_release(monkeypatch, body, sums)
    started = []
    monkeypatch.setattr(M.subprocess, "Popen",
                        lambda *a, **k: started.append(a) or None)
    assert M.self_update() == 0
    assert started and "СОШ" in capsys.readouterr().out.upper()
