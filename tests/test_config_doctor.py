"""Этап 4: миграции конфига (новые safety-ключи, сохранение своих) + doctor."""
from aipc.config import SAFETY_VERSION, load_config, save_config


def test_new_safety_keys_present():
    cfg = load_config()
    s = cfg["safety"]
    for key in ("confirm_timeout", "allow_minutes", "run_cmd_policy",
                "cmd_allowlist", "sensitive_windows_extra", "taint_guard",
                "taint_window", "max_calls_per_min", "loop_repeat",
                "max_download_mb", "allow_ssh_keys"):
        assert key in s, f"нет ключа {key}"
    assert cfg.get("installer", {}).get("auto_register") is False
    assert cfg.get("lang") == "en"


def test_user_additions_preserved_on_upgrade():
    cfg = load_config()
    cfg.setdefault("safety", {}).setdefault("deny_cmd", []).append("my custom ban 12345")
    cfg["safety"]["version"] = 1  # старый — спровоцировать апгрейд
    save_config(cfg)
    cfg2 = load_config()
    assert "my custom ban 12345" in " ".join(cfg2["safety"]["deny_cmd"])
    assert cfg2["safety"]["version"] == SAFETY_VERSION
    assert "mimikatz" in " ".join(cfg2["safety"]["deny_cmd"])


def test_doctor_runs():
    from aipc.maintenance import doctor

    out = doctor()
    assert isinstance(out, list) and out
    names = [n for n, _, _ in out]
    assert "python" in names and "deny-листы" in names
    py = [o for o in out if o[0] == "python"][0]
    assert py[1] is True  # тесты идут на 3.10+
    deny = [o for o in out if o[0] == "deny-листы"][0]
    assert deny[1] is True


def test_gen_tools_table_check():
    import subprocess
    import sys

    r = subprocess.run([sys.executable, "tools/gen_tools_table.py", "--check"],
                       capture_output=True, text=True, cwd=".",
                       encoding="utf-8", errors="replace")
    assert r.returncode == 0, r.stdout + r.stderr
