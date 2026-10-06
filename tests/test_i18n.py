"""i18n: EN — база, RU — опция. Меню не падает на неизвестном ключе."""
from aipc import i18n
from aipc.config import load_config, save_config


def _set_lang(lang: str) -> None:
    cfg = load_config()
    cfg["lang"] = lang
    save_config(cfg)


def test_default_lang_is_en():
    _set_lang("en")
    assert i18n.current_lang() == "en"
    assert i18n.t("menu.run") == "Launch AiPC-Core"
    assert i18n.t("menu.run.hint") == "background server, IDE-style handshake"


def test_lang_ru():
    _set_lang("ru")
    try:
        assert i18n.current_lang() == "ru"
        assert i18n.t("menu.run") == "Запустить AiPC-Core"
        assert i18n.t("menu.exit") == "Выход"
        assert i18n.t("setup.lang")  # пункт есть на обоих языках
    finally:
        _set_lang("en")


def test_every_en_key_has_ru_and_vice_versa():
    missing_ru = set(i18n.EN) - set(i18n.RU)
    missing_en = set(i18n.RU) - set(i18n.EN)
    assert not missing_ru, f"нет RU для: {sorted(missing_ru)}"
    assert not missing_en, f"нет EN для: {sorted(missing_en)}"


def test_hints_exist_for_menu_items():
    _set_lang("en")
    # пункты меню (метки действий) обязаны иметь пару label+hint в обоих языках
    for base in ("menu.run", "menu.stop", "menu.status", "menu.doctor",
                 "menu.update", "menu.setup", "menu.service", "menu.logs",
                 "menu.exit", "setup.mode", "setup.ide", "setup.browser",
                 "setup.ssh", "setup.lang", "setup.theme", "setup.back"):
        assert base in i18n.EN and base in i18n.RU, base
        assert f"{base}.hint" in i18n.EN and f"{base}.hint" in i18n.RU, base


def test_unknown_key_returns_fallback_or_key():
    _set_lang("en")
    assert i18n.t("no.such.key") == "no.such.key"
    assert i18n.t("no.such.key", "fb") == "fb"


def test_bad_lang_falls_back_to_en(monkeypatch):
    from aipc import i18n as m

    cfg = load_config()
    cfg["lang"] = "de"
    save_config(cfg)
    try:
        assert m.current_lang() == "en"
        assert m.t("menu.stop") == "Stop"
    finally:
        cfg = load_config()
        cfg["lang"] = "en"
        save_config(cfg)
