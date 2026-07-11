from app.rag import simple_rag


def test_chunk_ids_are_stable_and_document_version_changes(monkeypatch, tmp_path):
    policy = tmp_path / "company_policy.md"
    onboarding = tmp_path / "onboarding_playbook.md"
    policy.write_text("# Policy\n\n" + "refund " * 130, encoding="utf-8")
    onboarding.write_text("# Onboarding\n\nworkflow setup", encoding="utf-8")
    monkeypatch.setattr(simple_rag, "DOCS_DIR", tmp_path)
    first = simple_rag.SimpleRagIndex()
    first.build()
    first_chunk = first.chunks[0]

    policy.write_text(policy.read_text(encoding="utf-8") + "\n\n# New\n\nlegal escalation", encoding="utf-8")
    second = simple_rag.SimpleRagIndex()
    second.build()
    matching = next(chunk for chunk in second.chunks if chunk.doc_id == first_chunk.doc_id)
    assert matching.text == first_chunk.text
    assert matching.version != first_chunk.version


def test_knowledge_index_excludes_portfolio_documents():
    index = simple_rag.SimpleRagIndex()
    index.build()
    assert {chunk.source for chunk in index.chunks} == simple_rag.KNOWLEDGE_FILES
