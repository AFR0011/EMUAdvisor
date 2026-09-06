"""Corpus artifact loading and status reporting."""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from .demo import demo_chunks
from .schema import validate_chunk


DEFAULT_CORPUS_PATH = Path("artifacts/demo_corpus/latest/chunks.jsonl")
DEFAULT_METRICS_PATH = Path("artifacts/metrics/latest/metrics.json")


@dataclass(frozen=True)
class CorpusBundle:
    chunks: List[Dict[str, Any]]
    source: str
    path: Optional[Path]
    status: Dict[str, Any]
    mode: str = "artifact"
    fixture: bool = False


def load_corpus(
    path: Path = DEFAULT_CORPUS_PATH,
    *,
    mode: str,
    profile: str,
) -> CorpusBundle:
    mode = mode.strip().casefold()
    profile = profile.strip().casefold()
    if profile not in {"dev", "test", "production"}:
        raise RuntimeError("EMU_ADVISOR_PROFILE must be explicitly set to dev, test, or production")
    if mode not in {"fixture", "artifact"}:
        raise RuntimeError("EMU_ADVISOR_CORPUS_MODE must be explicitly set to fixture or artifact")
    if mode == "fixture":
        if profile not in {"dev", "test"}:
            raise RuntimeError("fixture corpus mode is allowed only in dev or test profiles")
        chunks = []
        for raw in demo_chunks():
            chunk = dict(raw)
            chunk["source_url"] = f"fixture://{str(chunk['chunk_id']).replace(':', '-')}"
            chunk["metadata"] = {**dict(chunk.get("metadata") or {}), "fixture": True, "official_source": False}
            chunks.append(chunk)
        return CorpusBundle(
            chunks=chunks,
            source="explicit_fixture",
            path=None,
            status=corpus_status(chunks, path=None),
            mode="fixture",
            fixture=True,
        )
    if path.exists():
        chunks = load_chunks_jsonl(path)
        return CorpusBundle(
            chunks=chunks,
            source="artifact",
            path=path,
            status=corpus_status(chunks, path=path),
            mode="artifact",
            fixture=False,
        )
    raise FileNotFoundError(f"artifact corpus chunks not found: {path}")


def load_chunks_jsonl(path: Path) -> List[Dict[str, Any]]:
    chunks: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            record = json.loads(line)
            validate_chunk(record)
            chunks.append(record)
    if not chunks:
        raise ValueError(f"no chunks found in {path}")
    return chunks


def write_chunks_jsonl(chunks: Iterable[Dict[str, Any]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for chunk in chunks:
            validate_chunk(chunk)
            handle.write(json.dumps(chunk, ensure_ascii=False, sort_keys=True) + "\n")


def corpus_status(chunks: List[Dict[str, Any]], *, path: Optional[Path]) -> Dict[str, Any]:
    languages = Counter(str(chunk.get("language")) for chunk in chunks)
    corpora = Counter(str(chunk.get("corpus")) for chunk in chunks)
    source_types = Counter(str(chunk.get("source_type")) for chunk in chunks)
    documents = {str(chunk.get("document_id")) for chunk in chunks}
    sources = {str(chunk.get("source_url")) for chunk in chunks}
    crawl_times = sorted({str(chunk.get("last_crawled_at")) for chunk in chunks if chunk.get("last_crawled_at")})
    return {
        "path": path.as_posix() if path and not path.is_absolute() else (path.name if path else None),
        "chunk_count": len(chunks),
        "document_count": len(documents),
        "source_count": len(sources),
        "languages": dict(languages),
        "corpora": dict(corpora),
        "source_types": dict(source_types),
        "last_crawled_at_min": crawl_times[0] if crawl_times else None,
        "last_crawled_at_max": crawl_times[-1] if crawl_times else None,
    }


def load_latest_metrics(path: Path = DEFAULT_METRICS_PATH) -> Dict[str, Any]:
    if not path.exists():
        return {"available": False, "path": str(path)}
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("schema_version") != "emu-advisor-automated-proxy/v2":
        return {
            "available": True,
            "path": str(path),
            "schema_version": payload.get("schema_version"),
            "legacy": True,
            "verified": False,
            "message": "Legacy automated proxy output; not semantic answer-quality evidence.",
        }
    payload.setdefault("available", True)
    payload.setdefault("path", str(path))
    payload.setdefault("legacy", False)
    payload.setdefault("verified", False)
    return payload
