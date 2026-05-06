#!/usr/bin/env python3
"""
Updates checkboxes in TASKS.md based on actual implementation state.

A Python file task is checked off when none of its public functions
raise NotImplementedError. Non-Python tasks (Figma, deployment, JS files)
are left unchanged — those are marked manually.

Run locally:  python scripts/progress.py
CI:           GitHub Actions runs this on every push that changes a .py file.
"""
import ast
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TASKS_FILE = ROOT / "TASKS.md"

# Matches:  - [ ] `some/path.py`  or  - [x] `some/path.py`
# Captures: (indent+bullet, mark, filepath, rest of line)
TASK_RE = re.compile(r'^(\s*- )\[([ x])\] `([^`]+\.py)`(.*)')


def file_has_stubs(path: Path) -> bool:
    """
    Return True if the file doesn't exist yet, or if any public function
    in the file still raises NotImplementedError.
    """
    if not path.exists():
        return True
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except SyntaxError:
        return True

    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if node.name.startswith("_") or node.name.startswith("test_"):
            continue
        for stmt in ast.walk(ast.Module(body=node.body, type_ignores=[])):
            if not isinstance(stmt, ast.Raise) or stmt.exc is None:
                continue
            exc = stmt.exc
            name = None
            if isinstance(exc, ast.Call) and isinstance(exc.func, ast.Name):
                name = exc.func.id
            elif isinstance(exc, ast.Name):
                name = exc.id
            if name == "NotImplementedError":
                return True

    return False


def update() -> dict[str, tuple[int, int]]:
    """
    Rewrite TASKS.md with updated checkboxes.
    Returns per-owner counts: {owner: (done, total)}.
    """
    raw = TASKS_FILE.read_text(encoding="utf-8")
    lines = raw.splitlines(keepends=True)

    current_owner = "Unknown"
    counts: dict[str, list[int]] = {}   # owner -> [done, total]
    changed_lines = []

    for line in lines:
        # Track which owner's section we're in
        owner_match = re.match(r'^## (\w+) —', line)
        if owner_match:
            current_owner = owner_match.group(1)
            counts.setdefault(current_owner, [0, 0])

        m = TASK_RE.match(line)
        if not m:
            changed_lines.append(line)
            continue

        bullet, current_mark, filepath_str, rest = m.groups()
        counts.setdefault(current_owner, [0, 0])
        counts[current_owner][1] += 1      # total

        still_stub = file_has_stubs(ROOT / filepath_str)
        new_mark = " " if still_stub else "x"

        if new_mark == "x":
            counts[current_owner][0] += 1  # done

        changed_lines.append(f"{bullet}[{new_mark}] `{filepath_str}`{rest}")

    TASKS_FILE.write_text("".join(changed_lines), encoding="utf-8")
    return {owner: (d, t) for owner, (d, t) in counts.items()}


if __name__ == "__main__":
    counts = update()

    total_done = total_all = 0
    for owner, (done, total) in counts.items():
        if total == 0:
            continue
        pct = int(done / total * 100)
        print(f"  {owner:<12} {done:>2}/{total:<2} Python file tasks done ({pct}%)")
        total_done += done
        total_all += total

    overall = int(total_done / total_all * 100) if total_all else 0
    print(f"\n  Overall: {total_done}/{total_all} ({overall}%)")
    print(f"\n  TASKS.md updated.")
