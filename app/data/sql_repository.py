from __future__ import annotations

from typing import Any

from sqlalchemy import Float, Integer, String, Text, UniqueConstraint, create_engine, select, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

from app.data.repositories import BusinessRepository
from app.security.context import PrincipalContext


class Base(DeclarativeBase):
    pass


class TenantRow:
    tenant_id: Mapped[str] = mapped_column(String(80), primary_key=True)


class Customer(TenantRow, Base):
    __tablename__ = "customers"
    customer_id: Mapped[str] = mapped_column(String(40), primary_key=True)
    customer_name: Mapped[str] = mapped_column(String(200))
    industry: Mapped[str] = mapped_column(String(120))
    plan: Mapped[str] = mapped_column(String(80))
    owner: Mapped[str] = mapped_column(String(120))
    health_score: Mapped[int] = mapped_column(Integer)


class Ticket(TenantRow, Base):
    __tablename__ = "tickets"
    ticket_id: Mapped[str] = mapped_column(String(40), primary_key=True)
    customer_id: Mapped[str] = mapped_column(String(40), index=True)
    status: Mapped[str] = mapped_column(String(40))
    priority: Mapped[str] = mapped_column(String(40))
    days_open: Mapped[int] = mapped_column(Integer)
    issue: Mapped[str] = mapped_column(Text)


class Order(TenantRow, Base):
    __tablename__ = "orders"
    order_id: Mapped[str] = mapped_column(String(40), primary_key=True)
    customer_id: Mapped[str] = mapped_column(String(40), index=True)
    amount_usd: Mapped[float] = mapped_column(Float)
    payment_status: Mapped[str] = mapped_column(String(40))
    due_date: Mapped[str] = mapped_column(String(20))


class Note(TenantRow, Base):
    __tablename__ = "crm_notes"
    note_id: Mapped[str] = mapped_column(String(40), primary_key=True)
    customer_id: Mapped[str] = mapped_column(String(40), index=True)
    date: Mapped[str] = mapped_column(String(20))
    note: Mapped[str] = mapped_column(Text)


class Task(TenantRow, Base):
    __tablename__ = "crm_tasks"
    __table_args__ = (UniqueConstraint("tenant_id", "idempotency_key", name="uq_task_tenant_idempotency"),)
    task_id: Mapped[str] = mapped_column(String(40), primary_key=True)
    customer_id: Mapped[str] = mapped_column(String(40), index=True)
    task: Mapped[str] = mapped_column(Text)
    due_date: Mapped[str] = mapped_column(String(20))
    owner: Mapped[str] = mapped_column(String(120))
    idempotency_key: Mapped[str] = mapped_column(String(200))


TABLE_MODELS = {
    "customers": Customer,
    "tickets": Ticket,
    "orders": Order,
    "notes": Note,
}


class SqlAlchemyBusinessRepository(BusinessRepository):
    def __init__(self, database_url: str) -> None:
        self.engine = create_engine(database_url, pool_pre_ping=True)

    def create_schema(self) -> None:
        Base.metadata.create_all(self.engine)

    def is_ready(self) -> bool:
        try:
            with self.engine.connect() as connection:
                connection.execute(text("SELECT 1"))
            return True
        except SQLAlchemyError:
            return False

    def _rows(self, model: type[Base], principal: PrincipalContext) -> list[dict[str, Any]]:
        with Session(self.engine) as session:
            self._set_tenant_context(session, principal.tenant_id)
            rows = session.scalars(select(model).where(model.tenant_id == principal.tenant_id)).all()
            return [
                {column.name: getattr(row, column.name) for column in model.__table__.columns if column.name != "tenant_id"}
                for row in rows
            ]

    def customers(self, principal: PrincipalContext) -> list[dict[str, Any]]:
        return self._rows(Customer, principal)

    def tickets(self, principal: PrincipalContext) -> list[dict[str, Any]]:
        return self._rows(Ticket, principal)

    def orders(self, principal: PrincipalContext) -> list[dict[str, Any]]:
        return self._rows(Order, principal)

    def notes(self, principal: PrincipalContext) -> list[dict[str, Any]]:
        return self._rows(Note, principal)

    def create_task(self, principal: PrincipalContext, task: dict[str, Any]) -> dict[str, Any]:
        import hashlib
        task_id = "TASK-" + hashlib.sha256(f"{principal.tenant_id}:{task['idempotency_key']}".encode()).hexdigest()[:12]
        with Session(self.engine) as session, session.begin():
            self._set_tenant_context(session, principal.tenant_id)
            existing = session.scalar(
                select(Task).where(Task.tenant_id == principal.tenant_id, Task.idempotency_key == task["idempotency_key"])
            )
            if existing is None:
                existing = Task(tenant_id=principal.tenant_id, task_id=task_id, **task)
                session.add(existing)
            return {
                "status": "created_task",
                "task_id": existing.task_id,
                "customer_id": existing.customer_id,
                "task": existing.task,
                "due_date": existing.due_date,
                "owner": existing.owner,
                "idempotency_key": existing.idempotency_key,
            }

    def _set_tenant_context(self, session: Session, tenant_id: str) -> None:
        if self.engine.dialect.name == "postgresql":
            session.execute(text("SELECT set_config('app.tenant_id', :tenant_id, true)"), {"tenant_id": tenant_id})

    def seed(self, tenant_id: str, records: dict[str, list[dict[str, Any]]]) -> None:
        with Session(self.engine) as session, session.begin():
            for kind, rows in records.items():
                model = TABLE_MODELS[kind]
                for row in rows:
                    session.merge(model(tenant_id=tenant_id, **row))
