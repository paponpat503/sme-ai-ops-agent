import os

import pytest

from app.rag.production import PgVectorRetriever


class DeterministicEmbeddings:
    dimensions = 1536
    def embed(self, texts):
        vectors = []
        for text in texts:
            vector = [0.0] * self.dimensions
            vector[0] = 1.0 if "refund" in text.lower() else 0.1
            vector[1] = 1.0 if "onboarding" in text.lower() else 0.1
            vectors.append(vector)
        return vectors


@pytest.mark.skipif(not os.getenv("TEST_POSTGRES_URL"), reason="TEST_POSTGRES_URL is not configured")
def test_pgvector_build_search_and_tenant_isolation():
    retriever = PgVectorRetriever(os.environ["TEST_POSTGRES_URL"], DeterministicEmbeddings(), min_score=0.1)
    retriever.build()
    assert retriever.search("refund", tenant_id="demo")
    assert retriever.search("refund", tenant_id="other") == []
