"""Этап 6.4: профили tools — состав, Bad-профиль, выигрыш в схеме."""
import json

from aipc.server import PROFILES, create_server, profile_tools


def _names(profile):
    return sorted(t.name for t in create_server(profile)._tool_manager.list_tools())


def test_profile_sets():
    assert profile_tools("full") is None
    assert set(profile_tools("minimal")) == set(PROFILES["minimal"])
    assert set(profile_tools("browser")) == set(PROFILES["browser"])
    try:
        profile_tools("nope")
    except ValueError:
        pass
    else:
        raise AssertionError("плохой профиль молча принят")


def test_minimal_registers_subset():
    names = _names("minimal")
    assert len(names) == len(PROFILES["minimal"]) == 12
    assert "screen_see" in names and "run_cmd" in names
    assert "ssh_exec" not in names and "browser_eval" not in names


def test_browser_registers_subset():
    names = _names("browser")
    assert len(names) == len(PROFILES["browser"]) == 20
    assert "browser_eval" in names and "web_search_pc" in names
    assert "ssh_exec" not in names


def test_full_registers_all():
    assert len(_names("full")) == 70


def test_profile_schema_win():
    """Замер выигрыша: суммарный размер JSON-схем по профилям."""
    import aipc.server as S

    wins = {}
    for prof in ("full", "browser", "minimal"):
        total = 0
        for t in create_server(prof)._tool_manager.list_tools():
            total += len(json.dumps(getattr(t, "parameters", {}) or {},
                                    ensure_ascii=False))
        wins[prof] = total
    assert wins["minimal"] < wins["browser"] < wins["full"]
    print(f"\nсхемы: full={wins['full']} browser={wins['browser']} "
          f"minimal={wins['minimal']} "
          f"(выигрыш minimal {100 * (1 - wins['minimal'] / wins['full']):.0f}%)")
