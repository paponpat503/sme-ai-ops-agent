from app.rag.production import HybridRetriever, PgVectorRetriever
from app.schemas.models import RagHit


class FakeRetriever:
    def __init__(self, hits):
        self.hits = hits
    def build(self):
        pass
    def search(self, query, top_k=3, tenant_id="demo"):
        return self.hits[:top_k]
    def is_ready(self):
        return True


def hit(doc_id, score=0.5):
    return RagHit(doc_id=doc_id, source="policy.md", score=score, text=doc_id)


def test_hybrid_rrf_rewards_results_from_both_retrievers():
    lexical = FakeRetriever([hit("lexical-only"), hit("shared")])
    semantic = FakeRetriever([hit("shared"), hit("semantic-only")])
    results = HybridRetriever(lexical, semantic).search("query", top_k=3)
    assert results[0].doc_id == "shared"
    assert {item.doc_id for item in results} == {"shared", "lexical-only", "semantic-only"}


def test_pgvector_rejects_non_postgres_database():
    class Embeddings:
        dimensions = 3
        def embed(self, texts):
            return [[0.0, 0.0, 0.0] for _ in texts]
    try:
        PgVectorRetriever("sqlite:///:memory:", Embeddings())
    except ValueError as exc:
        assert "PostgreSQL" in str(exc)
    else:
        raise AssertionError("Expected PostgreSQL-only validation")
