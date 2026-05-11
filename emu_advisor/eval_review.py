"""Human-review helpers for EMU Advisor evaluation sets."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from .corpus import load_chunks_jsonl
from .evaluation import EvaluationCase, load_cases


REVIEW_COLUMNS = [
    "case_id",
    "language",
    "expected_behavior",
    "category",
    "review_status",
    "question",
    "expected_source_urls",
    "expected_chunk_ids",
    "expected_answer_keywords",
    "expected_answer_text",
    "is_correct",
    "citation_ok",
    "human_label",
    "reviewer_notes",
]


def summarize_review_status(paths: Iterable[Path]) -> Dict[str, Any]:
    summaries = []
    total_cases = 0
    pending_cases = 0
    for path in paths:
        cases = load_cases(path)
        review_statuses: Dict[str, int] = {}
        missing_bindings = 0
        for case in cases:
            review_statuses[case.review_status] = review_statuses.get(case.review_status, 0) + 1
            if case.expected_behavior in {"answer", "conflict"} and not (case.expected_chunk_ids or case.expected_chunk_id):
                missing_bindings += 1
        total_cases += len(cases)
        pending_cases += sum(
            1
            for case in cases
            if "pending" in case.review_status or case.is_correct is None or case.citation_ok is None
        )
        summaries.append(
            {
                "path": str(path),
                "cases": len(cases),
                "review_statuses": review_statuses,
                "missing_chunk_bindings": missing_bindings,
            }
        )
    return {"case_sets": summaries, "total_cases": total_cases, "pending_cases": pending_cases}


def export_review_csv(cases_path: Path, out_path: Path) -> Dict[str, Any]:
    cases = load_cases(cases_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=REVIEW_COLUMNS)
        writer.writeheader()
        for case in cases:
            writer.writerow(_review_row(case))
    return {"cases": len(cases), "out": str(out_path), "review_columns": REVIEW_COLUMNS}


def bind_seed_cases(cases_path: Path, chunks_path: Path, out_path: Path) -> Dict[str, Any]:
    chunks = load_chunks_jsonl(chunks_path)
    by_source: Dict[str, List[Dict[str, Any]]] = {}
    for chunk in chunks:
        by_source.setdefault(str(chunk.get("source_url") or ""), []).append(chunk)

    bound = 0
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with cases_path.open("r", encoding="utf-8") as source, out_path.open("w", encoding="utf-8") as target:
        for line in source:
            if not line.strip():
                continue
            payload = json.loads(line)
            if payload.get("expected_behavior") in {"answer", "conflict"}:
                matches = _best_chunk_matches(payload, by_source.get(str(payload.get("expected_source_url") or ""), []))
                if matches:
                    payload["expected_chunk_ids"] = [str(match["chunk_id"]) for match in matches]
                    payload["expected_document_id"] = payload.get("expected_document_id") or str(matches[0]["document_id"])
                    payload["expected_chunk_id"] = payload.get("expected_chunk_id") or str(matches[0]["chunk_id"])
                    payload["review_status"] = "provisional_gold_seed_bound_pending_human_review"
                    bound += 1
            target.write(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n")
    return {"source_cases": str(cases_path), "chunks": str(chunks_path), "out": str(out_path), "bound_cases": bound}


def _best_chunk_matches(payload: Dict[str, Any], candidates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    keywords = [str(item).casefold() for item in payload.get("expected_answer_keywords", []) if item]
    quote_spans = [str(item).casefold() for item in payload.get("expected_quote_spans", []) if item]
    terms = keywords or quote_spans
    if not terms:
        return candidates[:1]
    scored = []
    for chunk in candidates:
        text = str(chunk.get("chunk_text") or "").casefold()
        score = sum(1 for term in terms if term and term in text)
        if score:
            scored.append((score, chunk))
    scored.sort(key=lambda item: item[0], reverse=True)
    return [chunk for _score, chunk in scored[:3]]


def _review_row(case: EvaluationCase) -> Dict[str, Any]:
    return {
        "case_id": case.case_id,
        "language": case.language,
        "expected_behavior": case.expected_behavior,
        "category": case.category,
        "review_status": case.review_status,
        "question": case.question,
        "expected_source_urls": "; ".join(case.expected_source_urls),
        "expected_chunk_ids": "; ".join(case.expected_chunk_ids),
        "expected_answer_keywords": "; ".join(case.expected_answer_keywords),
        "expected_answer_text": case.expected_answer_text,
        "is_correct": "" if case.is_correct is None else str(case.is_correct),
        "citation_ok": "" if case.citation_ok is None else str(case.citation_ok),
        "human_label": "",
        "reviewer_notes": case.notes,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Prepare and inspect EMU Advisor evaluation human-review artifacts.")
    sub = parser.add_subparsers(dest="cmd", required=True)

    status = sub.add_parser("status")
    status.add_argument("cases", type=Path, nargs="+")

    export = sub.add_parser("export-csv")
    export.add_argument("--cases", type=Path, required=True)
    export.add_argument("--out", type=Path, required=True)

    bind = sub.add_parser("bind-seed")
    bind.add_argument("--cases", type=Path, required=True)
    bind.add_argument("--chunks", type=Path, required=True)
    bind.add_argument("--out", type=Path, required=True)
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    if args.cmd == "status":
        result = summarize_review_status(args.cases)
    elif args.cmd == "export-csv":
        result = export_review_csv(args.cases, args.out)
    elif args.cmd == "bind-seed":
        result = bind_seed_cases(args.cases, args.chunks, args.out)
    else:
        raise ValueError(args.cmd)
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
