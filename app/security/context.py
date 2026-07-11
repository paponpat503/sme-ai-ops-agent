from __future__ import annotations

from contextvars import ContextVar
from dataclasses import dataclass
from typing import FrozenSet


ROLE_CAPABILITIES: dict[str, frozenset[str]] = {
    "viewer": frozenset({"crm:read", "billing:read", "policy:read", "draft:write"}),
    "operator": frozenset({"crm:read", "billing:read", "policy:read", "draft:write", "task:write"}),
    "admin": frozenset({"*"}),
}


@dataclass(frozen=True)
class PrincipalContext:
    tenant_id: str
    user_id: str
    roles: FrozenSet[str]
    request_id: str

    def can(self, capability: str) -> bool:
        granted = set().union(*(ROLE_CAPABILITIES.get(role, frozenset()) for role in self.roles))
        return "*" in granted or capability in granted


DEFAULT_PRINCIPAL = PrincipalContext(
    tenant_id="demo",
    user_id="demo-user",
    roles=frozenset({"operator"}),
    request_id="local",
)

_principal: ContextVar[PrincipalContext] = ContextVar("principal", default=DEFAULT_PRINCIPAL)


def get_principal() -> PrincipalContext:
    return _principal.get()


def set_principal(principal: PrincipalContext):
    return _principal.set(principal)


def reset_principal(token: object) -> None:
    _principal.reset(token)
