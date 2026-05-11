"""Index build CLI for local or Qdrant vector backends."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from .corpus import load_chunks_jsonl
from .embeddings import create_embedding_model
from .store import LocalVectorStore, QdrantVectorStore


def build_index(
    *,
    chunks_path: Path,
    backend: str,
    collection: str,
    qdrant_url: str,
    qdrant_path: Optional[str],
    embedding: str,
) -> Dict[str, Any]:
    chunks = load_chunks_jsonl(chunks_path)
    embedder = create_embedding_model(embedding)
    if backend == "qdrant":
        store = QdrantVectorStore(
            collection_name=collection,
            dimensions=embedder.dimensions,
            url=qdrant_url,
            path=qdrant_path,
        )
    elif backend == "local":
        store = LocalVectorStore(collection_name=collection, dimensions=embedder.dimensions)
    else:
        raise ValueError(f"unknown backend: {backend}")
    store.recreate_collection()
    indexed = store.upsert_chunks(chunks, embedder)
    if hasattr(store, "close"):
        store.close()
    return {
        "backend": backend,
        "collection": collection,
        "chunks": indexed,
        "embedding_model": embedder.metadata.model_name,
        "dimensions": embedder.dimensions,
    }


def check_index_health(
    *,
    backend: str,
    collection: str,
    qdrant_url: str,
    qdrant_path: Optional[str],
    embedding: str,
) -> Dict[str, Any]:
    embedder = create_embedding_model(embedding)
    if backend == "qdrant":
        store = QdrantVectorStore(
            collection_name=collection,
            dimensions=embedder.dimensions,
            url=qdrant_url,
            path=qdrant_path,
        )
    elif backend == "local":
        store = LocalVectorStore(collection_name=collection, dimensions=embedder.dimensions)
    else:
        raise ValueError(f"unknown backend: {backend}")
    try:
        health = store.health()
    finally:
        if hasattr(store, "close"):
            store.close()
    health.setdefault("embedding_model", embedder.metadata.model_name)
    return health


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build an EMU Advisor vector index.")
    sub = parser.add_subparsers(dest="cmd", required=True)
    build = sub.add_parser("build")
    build.add_argument("--chunks", type=Path, required=True)
    build.add_argument("--backend", choices=("qdrant", "local"), default="qdrant")
    build.add_argument("--collection", default="emu_regulations")
    build.add_argument("--qdrant-url", default="http://localhost:6333")
    build.add_argument("--qdrant-path", type=str, default=None, help="Use embedded local Qdrant storage instead of a server URL.")
    build.add_argument("--embedding", default="hash")
    health = sub.add_parser("health")
    health.add_argument("--backend", choices=("qdrant", "local"), default="qdrant")
    health.add_argument("--collection", default="emu_regulations")
    health.add_argument("--qdrant-url", default="http://localhost:6333")
    health.add_argument("--qdrant-path", type=str, default=None)
    health.add_argument("--embedding", default="hash")
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    if args.cmd == "build":
        result = build_index(
            chunks_path=args.chunks,
            backend=args.backend,
            collection=args.collection,
            qdrant_url=args.qdrant_url,
            qdrant_path=args.qdrant_path,
            embedding=args.embedding,
        )
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    if args.cmd == "health":
        result = check_index_health(
            backend=args.backend,
            collection=args.collection,
            qdrant_url=args.qdrant_url,
            qdrant_path=args.qdrant_path,
            embedding=args.embedding,
        )
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    raise ValueError(args.cmd)


if __name__ == "__main__":
    raise SystemExit(main())
