"""Fail publication CI when public-release invariants regress."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
GOLD = ROOT / "eval_sets" / "v1_gold.jsonl"


def verify_gold() -> None:
    rows = [json.loads(line) for line in GOLD.read_text(encoding="utf-8").splitlines() if line.strip()]
    if not rows:
        raise SystemExit("verified gold set is empty")
    failures = []
    for row in rows:
        if row.get("review_status") != "human_reviewed_verified":
            failures.append(f"{row.get('case_id')}: review_status={row.get('review_status')!r}")
        if row.get("is_correct") is not True:
            failures.append(f"{row.get('case_id')}: is_correct must be true")
        if row.get("citation_ok") is not True:
            failures.append(f"{row.get('case_id')}: citation_ok must be true")
    if failures:
        raise SystemExit("verified gold metadata regression:\n" + "\n".join(failures))
    print(f"verified gold metadata ok: {len(rows)} cases")


def verify_public_tree() -> None:
    required = [ROOT / "LICENSE", ROOT / "SECURITY.md", ROOT / "PUBLICATION.md", ROOT / "requirements-lock.txt"]
    missing = [str(path.relative_to(ROOT)) for path in required if not path.exists()]
    if missing:
        raise SystemExit("missing publication files: " + ", ".join(missing))

    forbidden = {
        "?admin_token=": "admin tokens must not be passed in URLs",
        "&admin_token=": "admin tokens must not be passed in URLs",
    }
    failures = []
    extensions = {".md", ".py", ".js", ".html", ".yml", ".yaml", ".txt"}
    for path in ROOT.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in extensions:
            continue
        if ".git" in path.parts or path == Path(__file__):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for token, reason in forbidden.items():
            if token in text:
                failures.append(f"{path.relative_to(ROOT)}: {reason}")
    if failures:
        raise SystemExit("publication tree regression:\n" + "\n".join(failures))
    print("publication tree guard ok")


def main() -> int:
    verify_gold()
    verify_public_tree()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
