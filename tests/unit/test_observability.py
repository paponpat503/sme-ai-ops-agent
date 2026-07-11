import logging

from app.observability import emit_event


def test_structured_event_redacts_sensitive_fields(caplog):
    with caplog.at_level(logging.INFO, logger="sme_ai_ops_agent"):
        emit_event("test", prompt="private", api_key="secret", tool_result={"customer": "private"}, request_id="req")
    message = caplog.records[-1].message
    assert "private" not in message
    assert "secret" not in message
    assert "req" in message
