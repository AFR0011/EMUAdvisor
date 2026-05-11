"""Board-demo readiness report generator."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from .audit_log import summarize_audit_log
from .corpus import load_latest_metrics
from .eval_review import summarize_review_status


ROOT = Path(__file__).resolve().parent.parent


def build_readiness_report(root: Path = ROOT) -> Dict[str, Any]:
    root = root.resolve()
    checks = [
        _file_check(root / "EMU_RAG_Current_System_Specs.md", "current product spec", root=root),
        _file_check(root / "docs" / "EMUAdvisor Full Analysis.md", "full analysis", root=root),
        _file_check(root / "docs" / "DEMO_STORYBOARD.md", "demo storyboard", root=root),
        _file_check(root / "docs" / "PUBLICATION_CHECKLIST.md", "publication checklist", root=root),
        _file_check(root / "eval_sets" / "v1_gold.jsonl", "candidate evaluation set", root=root),
        _file_check(root / "eval_sets" / "v1_hard.jsonl", "hard regression set", root=root),
    ]
    metrics_path = root / "artifacts" / "metrics" / "latest" / "metrics.json"
    metrics = load_latest_metrics(metrics_path)
    if metrics.get("available"):
        checks.append(
            {
                "name": "latest metrics artifact",
                "status": "pass",
                "detail": f"top5={metrics.get('retrieval_top5')} citation={metrics.get('citation_coverage')}",
            }
        )
    else:
        checks.append({"name": "latest metrics artifact", "status": "partial", "detail": "not present in artifacts"})
    review = summarize_review_status(
        [
            root / "eval_sets" / "v1_gold.jsonl",
            root / "eval_sets" / "v1_hard.jsonl",
            root / "eval_sets" / "emu_gold_seed.jsonl",
        ]
    )
    checks.append(
        {
            "name": "human-reviewed gold status",
            "status": "blocked" if review["pending_cases"] else "pass",
            "detail": f"{review['pending_cases']} cases still pending review",
        }
    )
    checks.append(
        {
            "name": "production admin token",
            "status": "pass" if os.getenv("EMU_ADVISOR_ADMIN_TOKEN") else "partial",
            "detail": "configured" if os.getenv("EMU_ADVISOR_ADMIN_TOKEN") else "not set for this local check",
        }
    )
    checks.append(
        {
            "name": "live Qdrant service",
            "status": "partial" if os.getenv("EMU_ADVISOR_QDRANT_URL") else "blocked",
            "detail": os.getenv("EMU_ADVISOR_QDRANT_URL") or "service-backed Qdrant not documented in environment",
        }
    )
    analytics = summarize_audit_log(root / "logs" / "audit.jsonl")
    checks.append(
        {
            "name": "local analytics log",
            "status": "pass" if analytics["events"] else "partial",
            "detail": f"{analytics['events']} audit events",
        }
    )
    status = _overall_status(checks)
    return {
        "status": status,
        "checks": checks,
        "review": review,
        "analytics": analytics,
        "summary": _status_sentence(status),
    }


def write_markdown_report(report: Dict[str, Any], out: Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Board Demo Readiness",
        "",
        f"Status: `{report['status']}`",
        "",
        report["summary"],
        "",
        "## Checks",
        "",
        "| Check | Status | Detail |",
        "|---|---|---|",
    ]
    for check in report["checks"]:
        lines.append(f"| {check['name']} | `{check['status']}` | {str(check['detail']).replace('|', '/')} |")
    lines.extend(
        [
            "",
            "## Non-Negotiable Limits",
            "",
            "- This is a board-demo readiness report, not a production approval.",
            "- Human-reviewed gold metrics remain blocked until manual labels are complete.",
            "- Production-style deployment remains blocked until service-backed Qdrant and target hardware are validated.",
            "- Generated mode remains extractive-first unless local model latency and answer quality are characterized.",
        ]
    )
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _file_check(path: Path, name: str, *, root: Path) -> Dict[str, str]:
    return {"name": name, "status": "pass" if path.exists() else "blocked", "detail": _display_path(path, root=root)}


def _display_path(path: Path, *, root: Path) -> str:
    try:
        return str(path.resolve().relative_to(root))
    except ValueError:
        return str(path)


def _overall_status(checks: List[Dict[str, Any]]) -> str:
    if any(check["status"] == "blocked" for check in checks):
        return "partial"
    if any(check["status"] == "partial" for check in checks):
        return "partial"
    return "demo_ready"


def _status_sentence(status: str) -> str:
    if status == "demo_ready":
        return "The local board demo has the required tracked evidence for a controlled demonstration."
    return "The local board demo is presentable with named gaps that must not be described as production-ready."


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate an EMU Advisor board-demo readiness report.")
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--out", type=Path, default=None)
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    report = build_readiness_report(args.root)
    if args.out:
        write_markdown_report(report, args.out)
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
