from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Protocol, Sequence

import httpx
from sqlalchemy import create_engine, text

from app.config import Settings
from app.rag.simple_rag import DocumentChunk, Retriever, SimpleRagIndex
from app.schemas.models import RagHit


class EmbeddingProvider(Protocol):
    dimensions: int
    def embed(self, texts: Sequence[str]) -> list[list[float]]: ...


class OpenAIEmbeddingProvider:
    def __init__(self, settings: Settings) -> None:
        self.model = settings.embedding_model
        self.dimensions = settings.embedding_dimensions
        self.timeout = settings.request_timeout_seconds
        self.base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY is required for pgvector retrieval.")
        response = httpx.post(
            f"{self.base_url}/embeddings",
            headers={"Authorization": f"Bearer {api_key}"},
            json={"model": self.model, "input": list(texts), "dimensions": self.dimensions},
            timeout=self.timeout,
        )
        response.raise_for_status()
        data = sorted(response.json()["data"], key=lambda item: item["index"])
        vectors = [item["embedding"] for item in data]
        if any(len(vector) != self.dimensions for vector in vectors):
            raise ValueError("Embedding provider returned an unexpected vector size.")
        return vectors


class PgVectorRetriever:
    def __init__(self, database_url: str, embeddings: EmbeddingProvider, min_score: float = 0.2) -> None:
        if not database_url.startswith(("postgresql://", "postgresql+psycopg://")):
            raise ValueError("PgVectorRetriever requires PostgreSQL.")
        self.engine = create_engine(database_url, pool_pre_ping=True)
        self.embeddings = embeddings
        self.min_score = min_score
        self._ready = False

    def build(self) -> None:
        chunks = _load_chunks()
        vectors = self.embeddings.embed([chunk.text for chunk in chunks])
        with self.engine.begin() as connection:
            for chunk, vector in zip(chunks, vectors, strict=True):
                connection.execute(
                    text(
                        """
                        INSERT INTO document_chunks
                            (tenant_id, doc_id, source, section, version, content, embedding)
                        VALUES
                            (:tenant_id, :doc_id, :source, :section, :version, :content, CAST(:embedding AS vector))
                        ON CONFLICT (tenant_id, doc_id) DO UPDATE SET
                            source=EXCLUDED.source, section=EXCLUDED.section,
                            version=EXCLUDED.version, content=EXCLUDED.content,
                            embedding=EXCLUDED.embedding
                        """
                    ),
                    {
                        "tenant_id": "demo",
                        "doc_id": chunk.doc_id,
                        "source": chunk.source,
                        "section": chunk.section,
                        "version": chunk.version,
                        "content": chunk.text,
                        "embedding": json.dumps(vector),
                    },
                )
        self._ready = True

    def search(self, query: str, top_k: int = 3, tenant_id: str = "demo") -> list[RagHit]:
        vector = self.embeddings.embed([query])[0]
        sql = text(
            """
            SELECT doc_id, source, section, version, content,
                   1 - (embedding <=> CAST(:embedding AS vector)) AS score
            FROM document_chunks
            WHERE tenant_id = :tenant_id
              AND 1 - (embedding <=> CAST(:embedding AS vector)) >= :min_score
            ORDER BY embedding <=> CAST(:embedding AS vector)
            LIMIT :top_k
            """
        )
        with self.engine.connect() as connection:
            rows = connection.execute(
                sql,
                {"embedding": json.dumps(vector), "tenant_id": tenant_id, "min_score": self.min_score, "top_k": top_k},
            ).mappings()
            return [
                RagHit(
                    doc_id=row["doc_id"], source=row["source"], section=row["section"],
                    version=row["version"], text=row["content"], score=float(row["score"]), tenant_id=tenant_id,
                )
                for row in rows
            ]

    def is_ready(self) -> bool:
        return self._ready


class HybridRetriever:
    def __init__(self, lexical: Retriever, semantic: Retriever, rrf_k: int = 60) -> None:
        self.lexical = lexical
        self.semantic = semantic
        self.rrf_k = rrf_k

    def build(self) -> None:
        self.lexical.build()
        self.semantic.build()

    def search(self, query: str, top_k: int = 3, tenant_id: str = "demo") -> list[RagHit]:
        candidates: dict[str, RagHit] = {}
        scores: dict[str, float] = {}
        for result_set in (
            self.lexical.search(query, max(top_k * 2, 10), tenant_id),
            self.semantic.search(query, max(top_k * 2, 10), tenant_id),
        ):
            for rank, hit in enumerate(result_set, 1):
                candidates[hit.doc_id] = hit
                scores[hit.doc_id] = scores.get(hit.doc_id, 0.0) + 1.0 / (self.rrf_k + rank)
        ranked = sorted(candidates, key=lambda doc_id: scores[doc_id], reverse=True)[:top_k]
        return [candidates[doc_id].model_copy(update={"score": scores[doc_id]}) for doc_id in ranked]

    def is_ready(self) -> bool:
        return self.lexical.is_ready() and self.semantic.is_ready()


def _load_chunks() -> list[DocumentChunk]:
    index = SimpleRagIndex()
    index.build()
    return index.chunks
