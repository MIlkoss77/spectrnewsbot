"""Compatibility scan: find constructs that break on the server's Python.

The production server runs an older Python than the dev machine, which is how
two outages happened: an f-string with a backslash (PEP 701, 3.12+) and an
``X | None`` annotation evaluated at import time (PEP 604; on 3.9 it raises
``TypeError: unsupported operand type(s) for |``).

    python tools_check_pyver.py                 # scan this project
    python tools_check_pyver.py --target 3.11   # check against another version
"""
import ast
import os
import sys

TARGET = (3, 11)

# Modules that do not need lazy annotations to be checked strictly.
FUTURE_ANNOTATIONS = "from __future__ import annotations"


def find_py_files(root: str) -> list:
    found = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in ("__pycache__", ".git", ".venv", "venv")]
        for name in filenames:
            if name.endswith(".py"):
                found.append(os.path.join(dirpath, name))
    return sorted(found)


def _has_future_annotations(tree: ast.Module) -> bool:
    for node in tree.body:
        if isinstance(node, ast.ImportFrom) and node.module == "__future__":
            if any(alias.name == "annotations" for alias in node.names):
                return True
    return False


def _is_pep604(node: ast.AST) -> bool:
    """True for 'X | Y' unions written in source (PEP 604)."""
    return isinstance(node, ast.BinOp) and isinstance(node.op, ast.BitOr)


def _annotation_nodes(tree: ast.Module) -> list:
    """Yield (lineno, annotation) pairs that Python evaluates at import time."""
    found = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            args = node.args
            all_args = list(args.posonlyargs) + list(args.args) + list(args.kwonlyargs)
            if args.vararg:
                all_args.append(args.vararg)
            if args.kwarg:
                all_args.append(args.kwarg)
            for arg in all_args:
                if arg.annotation is not None:
                    found.append((arg.annotation.lineno, arg.annotation))
            if node.returns is not None:
                found.append((node.returns.lineno, node.returns))
    return found


def check_file(path: str) -> list:
    issues = []
    src = open(path, encoding="utf-8").read()
    try:
        tree = ast.parse(src)
    except SyntaxError as exc:
        return [f"SyntaxError line {exc.lineno}: {exc.msg}"]

    lazy = _has_future_annotations(tree)

    # 1) PEP 701: backslash inside an f-string expression needs 3.12+
    if TARGET < (3, 12):
        for node in ast.walk(tree):
            if not isinstance(node, ast.FormattedValue):
                continue
            segment = ast.get_source_segment(src, node) or ""
            if "\\" in segment:
                issues.append(
                    f"line {node.lineno}: backslash inside f-string expression "
                    f"(needs 3.12+): {segment[:70]}"
                )

    # 2) PEP 604: 'X | None' in an evaluated annotation
    if TARGET < (3, 10) and not lazy:
        for lineno, annotation in _annotation_nodes(tree):
            if _is_pep604(annotation):
                segment = ast.get_source_segment(src, annotation) or ""
                issues.append(
                    f"line {lineno}: 'X | Y' annotation (PEP 604) is evaluated at import "
                    f"time on {TARGET[0]}.{TARGET[1]} — add "
                    f"'{FUTURE_ANNOTATIONS}': {segment[:60]}"
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

    print(f"No constructs incompatible with Python {TARGET[0]}.{TARGET[1]} found")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

