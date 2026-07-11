from pathlib import Path


def test_rls_migration_covers_every_tenant_table():
    source = Path("migrations/versions/0003_postgres_tenant_rls.py").read_text(encoding="utf-8")
    for table in ("customers", "tickets", "orders", "crm_notes", "crm_tasks", "document_chunks"):
        assert table in source
    assert "ENABLE ROW LEVEL SECURITY" in source
    assert "current_setting('app.tenant_id', true)" in source
