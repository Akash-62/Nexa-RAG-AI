import os

# Must set before any app imports so pydantic-settings picks it up
os.environ.setdefault("DATABASE_URL", "sqlite:///./test.db")
os.environ.setdefault("SECRET_KEY", "test-secret-key-do-not-use-in-production")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.db.session import get_db
from app.db.models import Base

TEST_DB_URL = "sqlite:///./test.db"

engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})

# Enable foreign key enforcement in SQLite
@event.listens_for(engine, "connect")
def set_sqlite_pragma(conn, _):
    conn.execute("PRAGMA foreign_keys=ON")

TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def _override_db():
    db = TestingSession()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)
    engine.dispose()
    try:
        if os.path.exists("test.db"):
            os.remove("test.db")
    except PermissionError:
        pass  # Windows: file still held by SQLite; cleaned up on next run


@pytest.fixture(autouse=True)
def override_db():
    app.dependency_overrides[get_db] = _override_db
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)
