from app.data.repositories import records_as_frame
from app.security.context import PrincipalContext


def test_empty_tenant_frames_preserve_business_schema():
    principal = PrincipalContext("other", "user", frozenset({"viewer"}), "test")
    assert list(records_as_frame("tickets", principal).columns) == [
        "ticket_id", "customer_id", "status", "priority", "days_open", "issue"
    ]
    assert records_as_frame("tickets", principal).empty
