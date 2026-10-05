"""Compatibility scan: find constructs that need Python 3.12+.

The production server runs Python 3.11, where PEP 701 does not exist yet, so an
f-string containing a backslash (or same-type nested quotes) is a SyntaxError.
The local dev machine runs 3.13 and accepts it, which is exactly how such a bug
reached the server. Run this before pushing.

    python tools_check_pyver.py            # scan this project
    python tools_check_pyver.py --target 3.11
"""
import ast
import os
import sys

TARGET = (3, 11)


def find_py_files(root: str) -> list:
    found = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in ("__pycache__", ".git", ".venv", "venv")]
        for name in filenames:
            if name.endswith(".py"):
                found.append(os.path.join(dirpath, name))
    return sorted(found)


def check_file(path: str) -> list:
    issues = []
    src = open(path, encoding="utf-8").read()
    try:
        tree = ast.parse(src)
    except SyntaxError as exc:
        return [f"SyntaxError line {exc.lineno}: {exc.msg}"]

    for node in ast.walk(tree):
        if not isinstance(node, ast.FormattedValue):
            continue
        segment = ast.get_source_segment(src, node) or ""
        if "\\" in segment and TARGET < (3, 12):
            issues.append(
                f"line {node.lineno}: backslash inside f-string expression "
                f"(needs 3.12+): {segment[:70]}"
            )
    return issues


def main() -> int:
    global TARGET
    if "--target" in sys.argv:
        raw = sys.argv[sys.argv.index("--target") + 1]
        TARGET = tuple(int(p) for p in raw.split("."))

    root = os.path.dirname(os.path.abspath(__file__))
    files = find_py_files(root)
    total_issues = 0

    print(f"Target Python: {TARGET[0]}.{TARGET[1]} | files: {len(files)}")
    for path in files:
        issues = check_file(path)
        if issues:
            total_issues += len(issues)
            print(f"\n{os.path.relpath(path, root)}")
            for issue in issues:
                print(f"  - {issue}")

    if total_issues:
        print(f"\n{total_issues} issue(s) would break on Python {TARGET[0]}.{TARGET[1]}")
        return 1

    print("No 3.12-only constructs found — safe for Python 3.11")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
