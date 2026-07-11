from __future__ import annotations

from pathlib import Path
import hashlib
from typing import Any, Protocol

import pandas as pd

from app.security.context import PrincipalContext, get_principal


class BusinessRepository(Protocol):
    def customers(self, principal: PrincipalContext) -> list[dict[str, Any]]: ...
    def tickets(self, principal: PrincipalContext) -> list[dict[str, Any]]: ...
    def orders(self, principal: PrincipalContext) -> list[dict[str, Any]]: ...
    def notes(self, principal: PrincipalContext) -> list[dict[str, Any]]: ...
    def create_task(self, principal: PrincipalContext, task: dict[str, Any]) -> dict[str, Any]: ...
    def is_ready(self) -> bool: ...


class CsvBusinessRepository:
    """Offline adapter for the synthetic, single-tenant demo dataset."""

    def __init__(self, data_dir: Path, tenant_id: str = "demo") -> None:
        self.data_dir = data_dir
        self.tenant_id = tenant_id

    def _read(self, name: str, principal: PrincipalContext) -> list[dict[str, Any]]:
        if principal.tenant_id != self.tenant_id:
            return []
        path = self.data_dir / name
        if not path.exists():
            raise FileNotFoundError(f"Missing data file: {path}")
        return pd.read_csv(path).to_dict(orient="records")

    def customers(self, principal: PrincipalContext) -> list[dict[str, Any]]:
        return self._read("customers.csv", principal)

    def tickets(self, principal: PrincipalContext) -> list[dict[str, Any]]:
        return self._read("tickets.csv", principal)

    def orders(self, principal: PrincipalContext) -> list[dict[str, Any]]:
        return self._read("orders.csv", principal)

    def notes(self, principal: PrincipalContext) -> list[dict[str, Any]]:
        return self._read("crm_notes.csv", principal)

    def create_task(self, principal: PrincipalContext, task: dict[str, Any]) -> dict[str, Any]:
        if principal.tenant_id != self.tenant_id:
            raise PermissionError("Tenant is not available in the demo adapter.")
        idempotency_key = str(task["idempotency_key"])
        task_id = "TASK-" + hashlib.sha256(f"{principal.tenant_id}:{idempotency_key}".encode()).hexdigest()[:12]
        return {"status": "created_demo_task", "task_id": task_id, **task}

    def is_ready(self) -> bool:
        return all((self.data_dir / name).is_file() for name in ("customers.csv", "tickets.csv", "orders.csv", "crm_notes.csv"))


DATA_DIR = Path(__file__).resolve().parents[2] / "data"
_repository: BusinessRepository = CsvBusinessRepository(DATA_DIR)
RECORD_COLUMNS = {
    "customers": ["customer_id", "customer_name", "industry", "plan", "owner", "health_score"],
    "tickets": ["ticket_id", "customer_id", "status", "priority", "days_open", "issue"],
    "orders": ["order_id", "customer_id", "amount_usd", "payment_status", "due_date"],
    "notes": ["note_id", "customer_id", "date", "note"],
}


def get_business_repository() -> BusinessRepository:
    return _repository


def set_business_repository(repository: BusinessRepository) -> None:
    global _repository
    _repository = repository


def records_as_frame(kind: str, principal: PrincipalContext | None = None) -> pd.DataFrame:
    principal = principal or get_principal()
    repository = get_business_repository()
    loader = getattr(repository, kind)
    return pd.DataFrame(loader(principal), columns=RECORD_COLUMNS[kind])
