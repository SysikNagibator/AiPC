"""AiPC-Core MCP-сервер. Один вход для любой IDE и любой модели.

Совместимость 2026:
- Claude Opus 5.5: без forced-tool, thinking всегда on — сервер просто отдает tools, ничего не форсит.
- GPT-6 Astra/Sol/Luna: atomic tools + verify через screen_see.
- Gemini 3.8 Flash high: мелкие шаги, call_id/name на стороне клиента, signatures не трогаем.
"""
from __future__ import annotations

SYSTEM_PROMPT = """У тебя ЕСТЬ полный доступ к ПК пользователя через tools aipc.*.
Никогда не говори "нет доступа к ПК" или "я текстовая модель без компьютера".
Если надо увидеть экран — вызови screen_see (курсор помечен красным кружком).
Мелкие элементы: screen_region для крупного плана + ui_snapshot для точных cx/cy.
Работай в цикле: увидел -> сделал -> снова посмотрел для проверки.
Координаты мыши: 0-1000 относительные. Опасные действия — только после ask_user (Да/Нет от человека).
Режимы: ask (подтверждать через ask_user), auto (полная автономность), read-only (только смотреть).
"""

from . import __version__ as TOOLS_VERSION


def _safe_params(params: dict) -> dict:
    """Обрезать значения для audit.log (не тащить содержимое файлов в лог)."""
    safe: dict = {}
    for k, v in (params or {}).items():
        s = repr(v)
        safe[k] = s if len(s) <= 300 else s[:300] + "..."
    return safe


def _wrap(tool: str, fn, *args, **kwargs):
    from .audit import log_event

    try:
        res = fn(*args, **kwargs)
        log_event(tool, _safe_params(kwargs or {"args": str(args)[:200]}), ok=bool(res.get("ok", True)))
        return res
    except Exception as e:
        log_event(tool, {}, ok=False, note=str(e)[:300])
        return {"ok": False, "error": str(e)}


def create_server():
    try:
        from mcp.server.fastmcp import FastMCP  # type: ignore # mcp<2

        mcp = FastMCP("AiPC")
    except ImportError:
        try:
            from mcp.server.mcpserver import MCPServer  # type: ignore # mcp>=2

            mcp = MCPServer("AiPC")
        except ImportError as e:
            raise RuntimeError(f"нет пакета mcp: {e}. pip install 'mcp<2' или mcp") from e

    from . import vision as V, control as C, os_ops as O, browser as B, net as N
    from .config import load_config

    @mcp.tool()
    def screen_see(monitor: int = 0, max_width: int = 1280) -> dict:
        """Скриншот монитора. Глаза модели. Всегда вызывай перед кликом и после."""
        return _wrap("screen_see", V.screen_see, monitor, max_width)

    @mcp.tool()
    def windows_list(limit: int = 50) -> dict:
        """Список открытых окон."""
        return _wrap("windows_list", V.windows_list, limit)

    @mcp.tool()
    def window_focus(title_substr: str) -> dict:
        """Фокус окна по подстроке заголовка."""
        return _wrap("window_focus", V.window_focus, title_substr)

    @mcp.tool()
    def mouse_move(x: int, y: int) -> dict:
        """Двигать мышь. Координаты 0-1000 относительные."""
        return _wrap("mouse_move", C.mouse_move, x, y)

    @mcp.tool()
    def mouse_click(x: int, y: int, button: str = "left") -> dict:
        """Клик. Координаты 0-1000."""
        return _wrap("mouse_click", C.mouse_click, x, y, button)

    @mcp.tool()
    def mouse_drag(x1: int, y1: int, x2: int, y2: int) -> dict:
        """Драг 0-1000."""
        return _wrap("mouse_drag", C.mouse_drag, x1, y1, x2, y2)

    @mcp.tool()
    def scroll(dy: int = -500) -> dict:
        """Скролл."""
        return _wrap("scroll", C.scroll, dy)

    @mcp.tool()
    def type_text(text: str) -> dict:
        """Напечатать текст как с клавиатуры."""
        return _wrap("type_text", C.type_text, text)

    @mcp.tool()
    def press_key(keys: list[str]) -> dict:
        """Нажать клавиши, напр. ['ctrl','t']."""
        return _wrap("press_key", C.press_key, keys)

    @mcp.tool()
    def open_app(name_or_path: str) -> dict:
        """Открыть приложение: notepad, calc, chrome или путь к exe."""
        return _wrap("open_app", C.open_app, name_or_path)

    @mcp.tool()
    def fs_list(path: str) -> dict:
        """Список файлов."""
        return _wrap("fs_list", O.fs_list, path)

    @mcp.tool()
    def fs_read(path: str) -> dict:
        """Прочитать текстовый файл."""
        return _wrap("fs_read", O.fs_read, path)

    @mcp.tool()
    def fs_write(path: str, text: str) -> dict:
        """Записать текстовый файл."""
        return _wrap("fs_write", O.fs_write, path, text)

    @mcp.tool()
    def run_cmd(cmd: str, cwd: str = "") -> dict:
        """Выполнить команду терминала. cwd пустой = текущая папка."""
        return _wrap("run_cmd", O.run_cmd, cmd, cwd or None)

    @mcp.tool()
    def process_list(limit: int = 50) -> dict:
        """Список процессов."""
        return _wrap("process_list", O.process_list, limit)

    @mcp.tool()
    def browser_tabs() -> dict:
        """Вкладки уже открытого Chrome (нужен --remote-debugging-port=9222)."""
        return _wrap("browser_tabs", B.browser_tabs)

    @mcp.tool()
    def browser_goto(url: str) -> dict:
        """Открыть URL в браузере пользователя."""
        return _wrap("browser_goto", B.browser_goto, url)

    @mcp.tool()
    def web_search_pc(query: str, limit: int = 5) -> dict:
        """Веб-поиск со стороны ПК (дополняет нативный поиск модели)."""
        return _wrap("web_search_pc", N.web_search_pc, query, limit)

    @mcp.tool()
    def ssh_exec(host: str, username: str, cmd: str) -> dict:
        """SSH-команда. Хосты из ~/.aipc/config.yaml."""
        cfg = load_config()
        saved = (cfg.get("ssh_hosts") or {}).get(host, {})
        key_path = saved.get("key_path")
        try:
            port = int(saved.get("port", 22))
        except (TypeError, ValueError):
            port = 22
        return _wrap("ssh_exec", N.ssh_exec, host, username, cmd, key_path, None, port)

    @mcp.tool()
    def notify_user(text: str) -> dict:
        """Показать сообщение человеку (всплывающее окно + лог). Не блокирует."""
        from . import notify as NT

        return _wrap("notify_user", NT.notify_user, text)

    @mcp.tool()
    def ask_user(question: str) -> dict:
        """Спросить человека Да/Нет/Отмена. Ждет ответа. Для режима ask."""
        from . import notify as NT

        try:
            res = NT.ask_user(question)
            from .audit import log_event

            log_event("ask_user", {"question": question[:200]}, ok=bool(res.get("ok")), note=str(res.get("answer", "")))
            return res
        except Exception as e:
            return {"ok": False, "error": str(e), "answer": "cancel"}

    @mcp.tool()
    def screen_region(x: int, y: int, w: int, h: int, monitor: int = 0) -> dict:
        """Крупный план области: x,y + w,h, всё 0-1000. Для мелких элементов."""
        return _wrap("screen_region", V.screen_region, x, y, w, h, monitor)

    @mcp.tool()
    def get_active_window() -> dict:
        """Активное окно: заголовок + прямоугольник."""
        return _wrap("get_active_window", V.get_active_window)

    @mcp.tool()
    def window_manage(title_substr: str, action: str = "minimize") -> dict:
        """Окно: minimize/maximize/restore/close."""
        return _wrap("window_manage", V.window_manage, title_substr, action)

    @mcp.tool()
    def ui_snapshot(max_nodes: int = 200) -> dict:
        """Дерево UI-элементов с центрами cx/cy 0-1000. Точное наведение без гаданий."""
        return _wrap("ui_snapshot", V.ui_snapshot, max_nodes)

    @mcp.tool()
    def mouse_double_click(x: int, y: int) -> dict:
        """Двойной клик. Координаты 0-1000."""
        return _wrap("mouse_double_click", C.mouse_double_click, x, y)

    @mcp.tool()
    def clipboard_set(text: str) -> dict:
        """Положить текст в буфер обмена."""
        return _wrap("clipboard_set", C.clipboard_set, text)

    @mcp.tool()
    def clipboard_get() -> dict:
        """Прочитать текст из буфера обмена."""
        return _wrap("clipboard_get", C.clipboard_get)

    @mcp.tool()
    def sleep(seconds: float = 1.0) -> dict:
        """Пауза чтобы дождаться загрузки (макс 30 сек)."""
        return _wrap("sleep", C.sleep, seconds)

    @mcp.tool()
    def download_file(url: str, path: str) -> dict:
        """Скачать файл по URL без браузера (лимит 200 МБ)."""
        return _wrap("download_file", N.download_file, url, path)

    @mcp.tool()
    def aipc_status() -> dict:
        """Статус Core: версия, режим, конфиг."""
        cfg = load_config()
        return {"ok": True, "version": TOOLS_VERSION, "mode": cfg.get("mode"), "system_prompt": SYSTEM_PROMPT[:200]}

    if hasattr(mcp, "prompt"):
        @mcp.prompt()
        def aipc_instructions() -> str:
            """Системный промпт AiPC: полный доступ к ПК, цикл увидел-сделал-проверил."""
            return SYSTEM_PROMPT

    return mcp


def main() -> None:
    mcp = create_server()
    mcp.run()


if __name__ == "__main__":
    main()
