from app.data.repositories import CsvBusinessRepository, DATA_DIR
from app.data.sql_repository import SqlAlchemyBusinessRepository


def test_csv_repository_readiness_requires_all_files(tmp_path):
    assert CsvBusinessRepository(DATA_DIR).is_ready()
    assert not CsvBusinessRepository(tmp_path).is_ready()


def test_sql_repository_readiness_checks_connection():
    repository = SqlAlchemyBusinessRepository("sqlite:///:memory:")
    assert repository.is_ready()
