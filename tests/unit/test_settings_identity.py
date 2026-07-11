import pytest
from pydantic import ValidationError

from app.config import Settings


def test_api_identity_rejects_unknown_roles():
    with pytest.raises(ValidationError):
        Settings.model_validate(
            {"api_keys": {"key": {"tenant_id": "demo", "user_id": "user", "roles": ["superuser"]}}}
        )


def test_api_identity_requires_nonempty_tenant_and_roles():
    with pytest.raises(ValidationError):
        Settings.model_validate(
            {"api_keys": {"key": {"tenant_id": "", "user_id": "user", "roles": []}}}
        )
