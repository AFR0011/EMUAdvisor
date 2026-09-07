"""Cross-platform Python syntax check used by CI."""

from __future__ import annotations

import ast
from pathlib import Path


def main() -> int:
    failed: list[tuple[str, str]] = []
    checked = 0
    for base in (Path("emu_advisor"), Path("tests"), Path("tools")):
        for path in base.rglob("*.py"):
            checked += 1
            try:
                ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            except Exception as exc:
                failed.append((str(path), repr(exc)))
    if failed:
        for path, error in failed:
            print(path, error)
        return 1
    print(f"syntax ok: {checked} files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
