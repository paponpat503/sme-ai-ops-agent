from __future__ import annotations

from app.config import get_settings
from app.rag.production import HybridRetriever, OpenAIEmbeddingProvider, PgVectorRetriever
from app.rag.simple_rag import Retriever, SimpleRagIndex
from app.telemetry import get_tracer


class RetrieverRuntime:
    def __init__(self) -> None:
        self.retriever: Retriever = SimpleRagIndex()
        self.error: str | None = None

    def build(self) -> None:
        settings = get_settings()
        self.error = None
        try:
            lexical = SimpleRagIndex()
            if settings.retriever_mode == "tfidf":
                retriever: Retriever = lexical
            else:
                if not settings.database_url:
                    raise RuntimeError("DATABASE_URL is required for vector retrieval.")
                semantic = PgVectorRetriever(
                    settings.database_url,
                    OpenAIEmbeddingProvider(settings),
                    min_score=settings.retrieval_min_score,
                )
                retriever = semantic if settings.retriever_mode == "pgvector" else HybridRetriever(lexical, semantic)
            retriever.build()
            self.retriever = retriever
        except Exception as exc:
            self.error = str(exc)
            raise

    def search(self, query: str, top_k: int = 3, tenant_id: str = "demo") -> list:
        with get_tracer().start_as_current_span("retrieval.search") as span:
            span.set_attribute("tenant.id", tenant_id)
            span.set_attribute("retrieval.mode", get_settings().retriever_mode)
            span.set_attribute("retrieval.top_k", top_k)
            hits = [] if self.error is not None else self.retriever.search(query, top_k, tenant_id)
            span.set_attribute("retrieval.hit_count", len(hits))
            return hits

    def is_ready(self) -> bool:
        return self.error is None and self.retriever.is_ready()


rag_runtime = RetrieverRuntime()
