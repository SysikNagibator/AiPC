"""Структурные тесты CLI: диспетчеры меню не должны тонуть в except-блоках."""
import ast
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent


def _funcs(path, names):
    tree = ast.parse((ROOT / path).read_text(encoding="utf-8"))
    out = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name in names:
            out[node.name] = node
    return out


def test_service_menu_dispatch_in_loop():
    funcs = _funcs("aipc/__main__.py", {"service_menu"})
    fn = funcs["service_menu"]
    loops = [n for n in fn.body if isinstance(n, ast.While)]
    assert loops, "нет цикла while в service_menu"
    body_kinds = [type(b).__name__ for b in loops[0].body]
    assert "If" in body_kinds, f"диспетчер if потерян из цикла: {body_kinds}"


def test_cmd_menu_dispatch():
    funcs = _funcs("aipc/__main__.py", {"cmd_menu", "_run_action"})
    assert "cmd_menu" in funcs and "_run_action" in funcs
    src = ast.dump(funcs["_run_action"])
    assert "start_core" in src and "show_doctor" in src and "service_menu" in src


def test_setup_menu_dispatch():
    funcs = _funcs("aipc/setup_wizard.py", {"setup_menu"})
    fn = funcs["setup_menu"]
    loops = [n for n in fn.body if isinstance(n, ast.While)]
    assert loops
    assert "If" in [type(b).__name__ for b in loops[0].body]
