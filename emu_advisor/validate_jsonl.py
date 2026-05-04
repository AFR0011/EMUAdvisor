"""Validate canonical EMU Advisor JSONL records."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

from .schema import SchemaValidationError, validate_chunk, validate_document


def iter_jsonl(path: Path) -> Iterable[Tuple[int, Dict[str, Any]]]:
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            payload = json.loads(stripped)
            if not isinstance(payload, dict):
                raise ValueError(f"line {line_number}: expected a JSON object")
            yield line_number, payload


def validate_file(path: Path, *, kind: str) -> List[str]:
    errors: List[str] = []
    validator = validate_chunk if kind == "chunk" else validate_document
    count = 0

    try:
        records = iter_jsonl(path)
        for line_number, record in records:
            count += 1
            try:
                validator(record)
            except SchemaValidationError as exc:
                for issue in exc.issues:
                    errors.append(f"{path}:{line_number}: {issue.format()}")
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        errors.append(f"{path}: {exc}")

    if count == 0 and not errors:
        errors.append(f"{path}: no records found")
    return errors


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path, help="JSONL file to validate")
    parser.add_argument(
        "--kind",
        choices=("chunk", "document"),
        default="chunk",
        help="Canonical record kind to validate",
    )
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    errors = validate_file(args.path, kind=args.kind)
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1

    print(f"{args.path}: valid {args.kind} JSONL")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
