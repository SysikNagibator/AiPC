"""Точка входа AiPC-Setup.exe (требует админа: копия в Program Files + PATH + MCP)."""
import sys


def main() -> int:
    from aipc.installer import is_admin, privileged_self_install, relaunch_as_admin

    print("=== AiPC от SYSIK : Setup ===")
    if not is_admin():
        print("Нужны права админа — перезапуск с UAC...")
        relaunch_as_admin()
        return 0
    code = privileged_self_install()
    print("Готово. Открой новый cmd и набери: aipc")
    input("Enter чтобы закрыть... ")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
