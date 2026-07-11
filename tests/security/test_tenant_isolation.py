from app.data.repositories import CsvBusinessRepository, DATA_DIR
from app.security.context import PrincipalContext


def test_csv_adapter_does_not_cross_tenants():
    repository = CsvBusinessRepository(DATA_DIR)
    other = PrincipalContext("other", "user", frozenset({"admin"}), "test")
    assert repository.customers(other) == []
    assert repository.tickets(other) == []
    assert repository.orders(other) == []
    assert repository.notes(other) == []
