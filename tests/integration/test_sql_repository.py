from app.data.repositories import CsvBusinessRepository, DATA_DIR
from app.data.sql_repository import SqlAlchemyBusinessRepository
from app.security.context import PrincipalContext


def test_sql_repository_contract_and_tenant_isolation(tmp_path):
    demo = PrincipalContext("demo", "user", frozenset({"operator"}), "test")
    other = PrincipalContext("other", "user", frozenset({"operator"}), "test")
    csv = CsvBusinessRepository(DATA_DIR)
    records = {
        "customers": csv.customers(demo),
        "tickets": csv.tickets(demo),
        "orders": csv.orders(demo),
        "notes": csv.notes(demo),
    }
    sql = SqlAlchemyBusinessRepository(f"sqlite:///{tmp_path / 'test.db'}")
    sql.create_schema()
    sql.seed("demo", records)

    assert sql.customers(demo) == records["customers"]
    assert len(sql.tickets(demo)) == len(records["tickets"])
    assert sql.customers(other) == []

    task = {
        "customer_id": "C001",
        "task": "Schedule support call",
        "due_date": "2026-08-01",
        "owner": "sales",
        "idempotency_key": "test-key-001",
    }
    first = sql.create_task(demo, task)
    second = sql.create_task(demo, task)
    assert first == second
    assert first["task_id"].startswith("TASK-")
