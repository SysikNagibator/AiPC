"""Системная информация, сеть, окружение. Только чтение."""
from __future__ import annotations

import os
import socket
import time as _time


def sys_info() -> dict:
    """Батарея, память, CPU, диски. Для решений модели (ждать/чистить/беречь батарею)."""
    out: dict = {"ok": True}
    try:
        import psutil  # type: ignore

        out["cpu_count"] = psutil.cpu_count()
        vm = psutil.virtual_memory()
        out["memory"] = {"total_mb": vm.total // 1048576, "available_mb": vm.available // 1048576,
                         "percent": vm.percent}
        try:
            bat = psutil.sensors_battery()
            out["battery"] = ({"percent": int(bat.percent), "plugged": bool(bat.power_plugged)}
                              if bat else None)
        except Exception:
            out["battery"] = None
        disks = []
        for part in psutil.disk_partitions(all=False):
            try:
                u = psutil.disk_usage(part.mountpoint)
                disks.append({"mount": part.mountpoint,
                              "free_gb": round(u.free / 1073741824, 1),
                              "percent": u.percent})
            except Exception:
                continue
        out["disks"] = disks
    except ImportError:
        return {"ok": False, "reason": "missing_dep", "error": "нет psutil"}
    except Exception as e:
        return {"ok": False, "reason": "error", "error": str(e)}
    try:
        out["hostname"] = socket.gethostname()
    except Exception:
        pass
    return out


def net_check(host: str, timeout: float = 5.0) -> dict:
    """Доступен ли хост. Формат 'example.com' (пробует 443, потом 80) или 'host:port'."""
    if not host or len(host) > 253:
        return {"ok": False, "reason": "bad_arg", "error": "пустой/битый host"}
    if ":" in host and host.count(":") == 1:
        name, port_s = host.rsplit(":", 1)
        try:
            ports = [int(port_s)]
        except ValueError:
            return {"ok": False, "reason": "bad_arg", "error": f"битый порт: {port_s}"}
    else:
        name, ports = host, [443, 80]
    errors = []
    for port in ports:
        try:
            t0 = _time.monotonic()
            with socket.create_connection((name, port), timeout=max(1.0, timeout)):
                ms = int((_time.monotonic() - t0) * 1000)
            return {"ok": True, "reachable": True, "host": name, "port": port, "latency_ms": ms}
        except Exception as e:
            errors.append(f"{port}: {e}")
    return {"ok": True, "reachable": False, "host": name, "error": "; ".join(errors)[:300]}


_SECRET_HINTS = ("key", "token", "secret", "password", "passwd", "pwd", "auth", "credential")


def env_get(name: str) -> dict:
    """Одна переменная окружения. Секреты (*KEY/*TOKEN/*SECRET...) не отдаю."""
    if not name or not name.strip():
        return {"ok": False, "reason": "bad_arg", "error": "пустое имя"}
    low = name.strip().lower()
    if any(h in low for h in _SECRET_HINTS):
        return {"ok": False, "reason": "denied", "error": "имена с секретами не читаю"}
    val = os.environ.get(name.strip())
    if val is None:
        return {"ok": False, "reason": "not_found", "error": f"нет переменной: {name}"}
    return {"ok": True, "name": name.strip(), "value": val[:2000]}
