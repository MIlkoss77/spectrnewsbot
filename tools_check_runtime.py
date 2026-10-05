"""Runtime scan: annotations evaluated at import time on older Python.

Two separate traps caused production outages on this project, and both were
invisible locally because the dev machine runs a newer Python:

1. PEP 701 — a backslash inside an f-string expression (Python 3.12+).
2. PEP 604 — ``X | None`` in a function annotation. This is evaluated at
   definition time on Python 3.9, and pydantic model classes do not support
   ``|``, so the import dies with
   ``TypeError: unsupported operand type(s) for |: 'ModelMetaclass' and 'NoneType'``.

On Python 3.10+ (2) is always safe, which is exactly why it slips through.
This script loads every module the real process loads and reports what breaks.

    python tools_check_runtime.py
"""
import importlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Same modules bot.py pulls in, in the same order.
MODULES = [
    "config",
    "content.style_guide",
    "content.prompts",
    "content.topic_pool",
    "content.generator",
    "scheduler",
    "handlers",
    "bot",
]


def main() -> int:
    print(f"Python {sys.version.split()[0]} on {sys.platform}")
    failures = []
    for name in MODULES:
        try:
            importlib.import_module(name)
        except Exception as exc:  # noqa: BLE001 - report everything
            failures.append((name, f"{type(exc).__name__}: {exc}"))
            print(f"  [FAIL] {name}: {type(exc).__name__}: {exc}")
        else:
            print(f"  [ok]   {name}")

    if failures:
        print(f"\n{len(failures)} module(s) failed to import — the bot would not start")
        print("On Python 3.9 the usual culprits are 'X | None' annotations and")
        print("'list[str]' at class scope; add 'from __future__ import annotations'.")
        return 1

    print("\nAll modules import cleanly")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
