import os
os.environ["TESTING"] = "1"
import pytest
from decimal import Decimal
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.app.main import app
from backend.app.db.database import Base, get_db
from backend.app.models.user import User, UserRole
from backend.app.models.unit import Unit
from backend.app.core.security import hash_password

# Use an isolated test database
TEST_DB_URL = "sqlite:///./test_property_rental.db"
test_engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    Base.metadata.drop_all(bind=test_engine)
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture
def db():
    connection = test_engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def client(db):
    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def test_users(db):
    # Manager
    manager = User(
        email="test_manager@property.com",
        password_hash=hash_password("Pass123!"),
        full_name="Test Manager",
        role=UserRole.PROPERTY_MANAGER.value
    )
    # Contractor 1
    contractor1 = User(
        email="test_bob@contractor.com",
        password_hash=hash_password("Pass123!"),
        full_name="Bob Contractor",
        role=UserRole.MAINTENANCE_CONTRACTOR.value
    )
    # Contractor 2
    contractor2 = User(
        email="test_alice@contractor.com",
        password_hash=hash_password("Pass123!"),
        full_name="Alice Contractor",
        role=UserRole.MAINTENANCE_CONTRACTOR.value
    )

    db.add_all([manager, contractor1, contractor2])
    db.commit()
    db.refresh(manager)
    db.refresh(contractor1)
    db.refresh(contractor2)

    return {
        "manager": manager,
        "contractor1": contractor1,
        "contractor2": contractor2,
    }


@pytest.fixture
def manager_token(client, test_users):
    res = client.post("/api/auth/login", json={
        "email": test_users["manager"].email,
        "password": "Pass123!"
    })
    return res.json()["access_token"]


@pytest.fixture
def contractor1_token(client, test_users):
    res = client.post("/api/auth/login", json={
        "email": test_users["contractor1"].email,
        "password": "Pass123!"
    })
    return res.json()["access_token"]


@pytest.fixture
def contractor2_token(client, test_users):
    res = client.post("/api/auth/login", json={
        "email": test_users["contractor2"].email,
        "password": "Pass123!"
    })
    return res.json()["access_token"]


@pytest.fixture
def test_unit(db):
    unit = Unit(
        unit_number="T-101",
        address="100 Test St, Apt 1",
        monthly_rent=Decimal("1200.00"),
        tenant_name="Alice Tenant",
        archived=False
    )
    db.add(unit)
    db.commit()
    db.refresh(unit)
    return unit
