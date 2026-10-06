"""Этап 2: системный промпт версионирован и содержит правила безопасности."""
import re

from aipc.server import PROMPT_VERSION, SYSTEM_PROMPT, create_server


def _instructions() -> str:
    import asyncio

    srv = create_server()
    res = srv.get_prompt("aipc_instructions")
    if asyncio.iscoroutine(res):
        res = asyncio.run(res)
    texts = []
    for m in res.messages:
        c = m.content
        t = getattr(c, "text", "") if not isinstance(c, str) else c
        if t:
            texts.append(t)
    assert texts, "пустой aipc_instructions"
    return "\n".join(texts)


def test_prompt_version_format():
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}\.\d+", PROMPT_VERSION), PROMPT_VERSION


def test_no_refusal_ban():
    assert "Никогда не говори" not in SYSTEM_PROMPT
    assert "нет доступа к ПК" not in SYSTEM_PROMPT


def test_honest_no_tools_clause():
    assert "aipc mcp" in SYSTEM_PROMPT


def test_safety_rules_present():
    must = ["увидел", "ask_user", "untrusted", "focus_type", "browser_eval",
            "ui_find", "screenshot_diff", "assert_ui", "reason", "hint",
            "ask", "auto", "read-only", "ровно один раз"]
    missing = [m for m in must if m not in SYSTEM_PROMPT]
    assert not missing, f"в промпте нет: {missing}"


def test_confirm_delete_send_rule():
    assert "удаление" in SYSTEM_PROMPT
    assert "отправка" in SYSTEM_PROMPT or "отправить" in SYSTEM_PROMPT


def test_no_blind_typing_rule():
    assert "вслепую" in SYSTEM_PROMPT


def test_instructions_match_prompt():
    assert _instructions() == SYSTEM_PROMPT
