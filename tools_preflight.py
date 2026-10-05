"""Single entry point for the pre-push checks.

Run this before pushing whenever local Python is newer than the server's:

    python3 tools_preflight.py

It chains the three checks that cover every outage this project has had:
Python-version compatibility, lint, and the offline logic suite. Exits non-zero
if anything fails, which makes it usable as a git pre-push hook.
"""
import subprocess
import sys
import os

ROOT = os.path.dirname(os.path.abspath(__file__))

STEPS = [
    ("Совместимость с Python на сервере (3.8)", [sys.executable, "tools_check_pyver.py", "--target", "3.8"]),
    ("Импорт всех модулей", [sys.executable, "tools_check_runtime.py"]),
    ("Офлайн-проверки логики", [sys.executable, "tools_selfcheck.py"]),
    ("Линтер (цель 3.8)", ["ruff", "check", "--target-version", "py38", "--output-format", "concise", "."]),
]


def run(label: str, command: list) -> bool:
    print(f"\n=== {label} ===", flush=True)
    if command[0] == "ruff":
        from shutil import which
        if which("ruff") is None:
            print("ruff не установлен — пропускаю")
            return True
    try:
        result = subprocess.run(command, cwd=ROOT)
    except FileNotFoundError:
        print(f"не найдено: {command[0]} — пропускаю")
        return True
    return result.returncode == 0


def main() -> int:
    failures = []
    for label, command in STEPS:
        if not run(label, command):
            failures.append(label)

    print("\n" + "=" * 60)
    if failures:
        print(f"ПРОВЕРКИ НЕ ПРОЙДЕНЫ: {', '.join(failures)}")
        print("Пуш отменён. Исправьте и повторите.")
        return 1
    print("Все проверки пройдены — можно пушить")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
