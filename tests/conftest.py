import pytest

from spec_manager.db import init_db, make_engine
from spec_manager.store import Store


@pytest.fixture
def store():
    engine = make_engine("sqlite:///:memory:")
    init_db(engine)
    return Store(engine)


@pytest.fixture
def client(store):
    from fastapi.testclient import TestClient

    from spec_manager.api import create_app

    return TestClient(create_app(store=store))
