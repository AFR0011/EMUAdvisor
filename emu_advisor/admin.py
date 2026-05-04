"""Admin snapshot, diff, and activation workflow."""

from __future__ import annotations

import json
import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping

from .schema import validate_chunk


@dataclass(frozen=True)
class SnapshotDiff:
    added: List[str]
    removed: List[str]
    changed: List[str]

    def as_dict(self) -> Dict[str, List[str]]:
        return {"added": self.added, "removed": self.removed, "changed": self.changed}


def write_snapshot(chunks: Iterable[Mapping[str, Any]], snapshot_dir: Path, *, label: str) -> Path:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    target = snapshot_dir / f"{timestamp}_{_safe_label(label)}"
    target.mkdir(parents=True, exist_ok=False)

    records = [dict(chunk) for chunk in chunks]
    for record in records:
        validate_chunk(record)

    chunks_path = target / "chunks.jsonl"
    with chunks_path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")

    manifest = {
        "label": label,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "chunk_count": len(records),
        "sources": _manifest_sources(records),
    }
    (target / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    return target


def diff_snapshots(old_snapshot: Path, new_snapshot: Path) -> SnapshotDiff:
    old_sources = _load_manifest(old_snapshot)["sources"]
    new_sources = _load_manifest(new_snapshot)["sources"]
    old_keys = set(old_sources)
    new_keys = set(new_sources)
    common = old_keys & new_keys
    changed = sorted(key for key in common if old_sources[key]["version_hash"] != new_sources[key]["version_hash"])
    return SnapshotDiff(
        added=sorted(new_keys - old_keys),
        removed=sorted(old_keys - new_keys),
        changed=changed,
    )


def activate_snapshot(snapshot: Path, active_pointer: Path) -> None:
    if not (snapshot / "chunks.jsonl").exists():
        raise FileNotFoundError(f"snapshot missing chunks.jsonl: {snapshot}")
    active_pointer.parent.mkdir(parents=True, exist_ok=True)
    active_pointer.write_text(str(snapshot.resolve()), encoding="utf-8")


def copy_active_chunks(active_pointer: Path, target_path: Path) -> None:
    snapshot_path = Path(active_pointer.read_text(encoding="utf-8").strip())
    source = snapshot_path / "chunks.jsonl"
    if not source.exists():
        raise FileNotFoundError(f"active snapshot missing chunks.jsonl: {source}")
    target_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, target_path)


def _manifest_sources(records: List[Mapping[str, Any]]) -> Dict[str, Dict[str, Any]]:
    sources: Dict[str, Dict[str, Any]] = {}
    for record in records:
        document_id = str(record["document_id"])
        current = sources.setdefault(
            document_id,
            {
                "source_url": record["source_url"],
                "source_title": record["source_title"],
                "language": record["language"],
                "corpus": record["corpus"],
                "source_type": record["source_type"],
                "version_hash": record["version_hash"],
                "chunks": 0,
            },
        )
        current["chunks"] += 1
    return sources


def _load_manifest(snapshot: Path) -> Dict[str, Any]:
    return json.loads((snapshot / "manifest.json").read_text(encoding="utf-8"))


def _safe_label(label: str) -> str:
    import re

    return re.sub(r"[^a-zA-Z0-9_.-]+", "-", label).strip("-") or "snapshot"
