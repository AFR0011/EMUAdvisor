"""Fail publication CI when public-release invariants regress."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
GOLD = ROOT / "eval_sets" / "v1_gold.jsonl"


def verify_evaluation_provenance() -> None:
    rows = [json.loads(line) for line in GOLD.read_text(encoding="utf-8").splitlines() if line.strip()]
    if not rows:
        raise SystemExit("assistant-curated regression set is empty")
    failures = []
    for row in rows:
        if row.get("review_status") != "assistant_curated_pending_independent_review":
            failures.append(f"{row.get('case_id')}: review_status={row.get('review_status')!r}")
        if row.get("is_correct") is not None:
            failures.append(f"{row.get('case_id')}: is_correct must remain null pending independent review")
        if row.get("citation_ok") is not None:
            failures.append(f"{row.get('case_id')}: citation_ok must remain null pending independent review")
        note = str(row.get("notes") or "").casefold()
        if "human-reviewed" in note or "university staff" in note:
            failures.append(f"{row.get('case_id')}: unsupported human-review note")
    if failures:
        raise SystemExit("evaluation provenance regression:\n" + "\n".join(failures))
    print(f"assistant-curated pending-review metadata ok: {len(rows)} cases")


def verify_human_review_contract(row: dict) -> None:
    """Reject future self-certified human-review labels without durable evidence."""
    if row.get("review_status") != "human_reviewed_verified":
        return
    evidence = row.get("review_evidence")
    required = {"reference", "dataset_sha256", "reviewed_at", "reviewer_role"}
    if not isinstance(evidence, dict) or not required.issubset(evidence) or row.get("is_correct") is not True or row.get("citation_ok") is not True:
        raise ValueError("human_reviewed_verified requires correctness judgments and a durable review_evidence reference")


def verify_public_tree() -> None:
    required = [ROOT / "LICENSE", ROOT / "SECURITY.md", ROOT / "PUBLICATION.md", ROOT / "requirements-lock.txt"]
    missing = [str(path.relative_to(ROOT)) for path in required if not path.exists()]
    if missing:
        raise SystemExit("missing publication files: " + ", ".join(missing))

    forbidden = {
        "?admin_token=": "admin tokens must not be passed in URLs",
        "&admin_token=": "admin tokens must not be passed in URLs",
        "reviewed by university staff": "unsupported university-staff review claim",
        "verified human-reviewed gold": "unsupported verified-gold claim",
    }
    failures = []
    claim_audit_records = {
        Path("docs/CLAIM_REGISTER.md"),
        Path("docs/EVIDENCE_MAP.md"),
    }
    extensions = {".md", ".py", ".js", ".html", ".yml", ".yaml", ".txt"}
    for path in ROOT.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in extensions:
            continue
        relative = path.relative_to(ROOT)
        if (
            ".git" in path.parts
            or path == Path(__file__)
            or relative in claim_audit_records
            or any(part in {"artifacts", "logs", ".old"} for part in path.parts)
        ):
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
    verify_evaluation_provenance()
    verify_public_tree()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
