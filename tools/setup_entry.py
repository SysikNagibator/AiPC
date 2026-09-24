"""Точка входа AiPC-Setup.exe (требует админа, ставит команду aipc в PATH)."""
import sys


def main() -> int:
    from aipc.installer import add_to_system_path, install_dir, install_self_to_program_files, is_admin, relaunch_as_admin

    print("=== AiPC от Sysik : Setup ===")
    if not is_admin():
        print("Нужны права админа — перезапуск с UAC...")
        relaunch_as_admin()
        return 0
    ok1, msg1 = install_self_to_program_files()
    print(f"[1/2] {msg1}")
    ok2, msg2 = add_to_system_path(install_dir())
    print(f"[2/2] {msg2}")
    print("Готово. Открой новый cmd и набери: aipc")
    input("Enter чтобы закрыть... ")
    return 0 if (ok1 and ok2) else 1


if __name__ == "__main__":
    raise SystemExit(main())
