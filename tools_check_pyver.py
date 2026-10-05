"""Compatibility scan: find constructs that break on the server's Python.

The production server runs Python 3.8 while the dev machine runs 3.13, which is
how two outages happened: an f-string with a backslash (PEP 701, 3.12+) and an
``X | None`` annotation evaluated at import time (PEP 604; on 3.8 and 3.9 it
raises ``TypeError: unsupported operand type(s) for |``).

    python tools_check_pyver.py                 # scan against the server target
    python tools_check_pyver.py --target 3.12   # check against another version
"""
import ast
import os
import re
import sys

TARGET = (3, 8)

# Modules that do not need lazy annotations to be checked strictly.
FUTURE_ANNOTATIONS = "from __future__ import annotations"


# Directories that hold other people's code or generated files. Scanning them
# reports incompatibilities that have nothing to do with this project — a
# hidden tool directory on one machine was enough to fail the check there while
# it passed everywhere else.
SKIP_DIRS = {
    "__pycache__", ".git", ".venv", "venv", "env", ".env",
    ".mypy_cache", ".pytest_cache", ".ruff_cache", "node_modules",
    "site-packages", ".selfcheck_state",
}


def find_py_files(root: str) -> list:
    found = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [
            d for d in dirnames
            if d not in SKIP_DIRS and not d.startswith(".")
        ]
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


def _mask_docstrings_and_comments(src: str, tree: ast.Module) -> str:
    """Blank out docstrings and comments, keeping line numbers intact.

    Documentation legitimately shows f-string examples, and those examples must
    not be reported as real code. Lines are replaced character-wise with spaces
    so every offset stays valid.
    """
    lines = src.split("\n")
    blanked = [False] * len(lines)

    def mask_range(start_line: int, end_line: int) -> None:
        for index in range(start_line - 1, min(end_line, len(lines))):
            blanked[index] = True

    for node in ast.walk(tree):
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant) \
                and isinstance(node.value.value, str):
            mask_range(node.lineno, getattr(node, "end_lineno", node.lineno))

    result = []
    for index, line in enumerate(lines):
        if blanked[index]:
            result.append(" " * len(line))
            continue
        hash_pos = line.find("#")
        if hash_pos != -1:
            result.append(line[:hash_pos] + " " * (len(line) - hash_pos))
        else:
            result.append(line)
    return "\n".join(result)


def _extract_expressions(body: str) -> list:
    """Return (offset, text) of every top-level {...} expression in an f-string body.

    Brace matching is done on the text instead of using AST columns: the byte
    offsets reported for FormattedValue differ between Python versions, and on
    3.8 they made the enclosing literal look like part of the expression. Text
    scanning behaves identically everywhere. Doubled braces are literal text in
    f-strings and are skipped.
    """
    found = []
    depth = 0
    start = None
    index = 0
    length = len(body)

    while index < length:
        char = body[index]
        if char == "{" and body[index:index + 2] == "{{" and depth == 0:
            index += 2
            continue
        if char == "}" and body[index:index + 2] == "}}" and depth == 0:
            index += 2
            continue
        if char == "{":
            if depth == 0:
                start = index + 1
            depth += 1
        elif char == "}":
            if depth == 1 and start is not None:
                found.append((start, body[start:index]))
                start = None
            depth = max(0, depth - 1)
        index += 1
    return found


def _fstring_issues(src: str, tree: ast.Module) -> list:
    """Check f-strings against the pre-3.12 rules, on the raw source text.

    Two things were illegal before 3.12 and both are reported:
      * a backslash inside an expression part, e.g. f"{'\n'.join(x)}"
      * reusing the enclosing quote inside an expression, e.g. f"{fn(x, 'y')}"
    A backslash in the literal part (f"a\\nb{x}") was always legal, and flagging
    it produced 53 false alarms on a real checkout.
    """
    issues = []
    text = _mask_docstrings_and_comments(src, tree)
    pattern = re.compile(r"""(?<![A-Za-z0-9_])([fF][rR]?|[rR][fF])(\"\"\"|'''|\"|')""")

    for match in pattern.finditer(text):
        quote = match.group(2)
        body_start = match.end()
        start_line = text.count("\n", 0, match.start()) + 1

        end = text.find(quote, body_start) if quote in ('"""', "'''") \
            else text.find("\n", body_start)
        body = text[body_start:end if end != -1 else len(text)]
        body_line = start_line

        for offset, expression in _extract_expressions(body):
            if not expression:
                continue
            expr_line = body_line + body.count("\n", 0, offset)
            snippet = expression[:70]

            if "\\" in expression:
                issues.append(
                    f"line {expr_line}: backslash inside an f-string expression "
                    f"(needs 3.12+): {{{snippet}}}"
                )
            if quote in expression:
                issues.append(
                    f"line {expr_line}: the f-string quote {quote!r} is reused inside its "
                    f"expression (needs 3.12+): {{{snippet}}}"
                )
    return issues


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


def _line_end_columns(src_lines: list) -> list:
    """Byte length of every source line, for clamping column offsets."""
    return [len(line.encode("utf-8")) for line in src_lines]


def _safe_segment(src_lines: list, line_ends: list, node) -> str:
    """Source text of a node, without the Python 3.8 get_source_segment bug.

    Python 3.8 implements ast.get_source_segment by encoding the line to bytes,
    slicing at byte offsets and decoding the result, which splits multi-byte
    characters and raises UnicodeDecodeError on any line with Cyrillic text.
    Columns are clamped to the line and decoded with errors='replace' instead.
    """
    lineno = getattr(node, "lineno", None)
    if not lineno or lineno > len(src_lines):
        return ""
    line = src_lines[lineno - 1]
    raw = line.encode("utf-8")
    start = min(max(getattr(node, "col_offset", 0), 0), len(raw))
    end = getattr(node, "end_col_offset", None)
    if end is None or getattr(node, "end_lineno", lineno) != lineno:
        end = line_ends[lineno - 1]
    end = min(max(end, start), len(raw))
    return raw[start:end].decode("utf-8", errors="replace")


def check_file(path: str) -> list:
    """Return compatibility problems in one file.

    Any unexpected failure is reported as an issue for that file instead of
    killing the whole scan, so the real cause is always visible.
    """
    issues = []
    try:
        with open(path, encoding="utf-8") as handle:
            src = handle.read()
    except OSError as exc:
        return [f"не читается: {type(exc).__name__}: {exc}"]
    except UnicodeDecodeError as exc:
        return [f"не UTF-8: {exc}"]

    try:
        tree = ast.parse(src)
    except SyntaxError as exc:
        return [f"SyntaxError line {exc.lineno}: {exc.msg}"]
    except Exception as exc:  # noqa: BLE001 - surface anything the parser raises
        return [f"{type(exc).__name__} при разборе: {exc}"]

    lazy = _has_future_annotations(tree)
    src_lines = src.split("\n")
    line_ends = _line_end_columns(src_lines)

    # 1) PEP 701: before 3.12 an f-string could not contain a backslash in its
    # expression part, nor reuse its own quote there. Both crashed production,
    # so both are reported. The check works on the source text, not on AST
    # offsets, because those differ between Python versions.
    if TARGET < (3, 12):
        issues.extend(_fstring_issues(src, tree))

    # 2) PEP 604: 'X | None' in an evaluated annotation
    if TARGET < (3, 10) and not lazy:
        for lineno, annotation in _annotation_nodes(tree):
            if _is_pep604(annotation):
                segment = _safe_segment(src_lines, line_ends, annotation)
                issues.append(
                    f"line {lineno}: 'X | Y' annotation (PEP 604) is evaluated at import "
                    f"time on {TARGET[0]}.{TARGET[1]} — add "
                    f"'{FUTURE_ANNOTATIONS}': {segment[:60]}"
                )

    # 3) API added after 3.8
    if TARGET < (3, 9):
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                if node.func.attr in ("removeprefix", "removesuffix"):
                    issues.append(
                        f"line {node.lineno}: str.{node.func.attr}() needs 3.9+, "
                        f"not available on {TARGET[0]}.{TARGET[1]}"
                    )
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                if node.func.id == "anext":
                    issues.append(f"line {node.lineno}: anext() needs 3.10+")

    return issues


def main() -> int:
    global TARGET
    if "--target" in sys.argv:
        index = sys.argv.index("--target")
        if len(sys.argv) <= index + 1:
            print("нужно значение: --target 3.8")
            return 2
        raw = sys.argv[index + 1]
        try:
            TARGET = tuple(int(p) for p in raw.split("."))
        except ValueError:
            print(f"не разобрал версию: {raw!r}")
            return 2

    verbose = "-v" in sys.argv or "--verbose" in sys.argv
    root = os.path.dirname(os.path.abspath(__file__))
    files = find_py_files(root)
    total_issues = 0

    print(f"Target Python: {TARGET[0]}.{TARGET[1]} | files: {len(files)} | "
          f"разбираю интерпретатором {sys.version.split()[0]}", flush=True)
    for path in files:
        rel = os.path.relpath(path, root)
        if verbose:
            print(f"  проверяю {rel}", flush=True)
        try:
            issues = check_file(path)
        except Exception as exc:  # noqa: BLE001 - never lose the cause
            import traceback
            issues = [f"ВНУТРЕННЯЯ ОШИБКА ПРОВЕРКИ: {type(exc).__name__}: {exc}"]
            traceback.print_exc()
        if issues:
            total_issues += len(issues)
            print(f"\n{rel}", flush=True)
            for issue in issues:
                print(f"  - {issue}", flush=True)

    if total_issues:
        print(f"\n{total_issues} issue(s) would break on Python {TARGET[0]}.{TARGET[1]}",
              flush=True)
        return 1

    print(f"No constructs incompatible with Python {TARGET[0]}.{TARGET[1]} found", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

