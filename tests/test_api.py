import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database import Base, get_db
from app.main import app
from app.models import User
from app.auth import get_password_hash

SQLALCHEMY_DATABASE_URL = "sqlite:///./test_daycare.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(scope="session", autouse=True)
def setup_database():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client():
    db = TestingSessionLocal()
    try:
        tables = [User.__table__]
        for table in tables:
            db.execute(table.delete())
        db.commit()
    finally:
        db.close()
    return TestClient(app)


@pytest.fixture
def db_session():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def test_user(db_session):
    from app.models import User as UserModel
    user = UserModel(
        email="test@example.com",
        username="testuser",
        hashed_password=get_password_hash("TestPass123"),
        role="admin",
        is_active=True
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return {
        "id": user.id,
        "email": user.email,
        "username": user.username,
        "password": "TestPass123",
        "role": user.role
    }


@pytest.fixture
def auth_token(client, test_user):
    response = client.post(
        "/api/v1/auth/token",
        data={"username": test_user["email"], "password": test_user["password"]}
    )
    assert response.status_code == 200, f"Login failed: {response.json()}"
    return response.json()["access_token"]


@pytest.fixture
def authorized_client(client, auth_token):
    client.headers = {"Authorization": f"Bearer {auth_token}"}
    return client


class TestHealthEndpoint:
    def test_health_check(self, client):
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data


class TestAuthRegistration:
    def test_register_success(self, client):
        response = client.post("/api/v1/auth/register", json={
            "email": "new@example.com",
            "username": "newuser",
            "password": "SecurePass1",
            "role": "staff"
        })
        assert response.status_code == 201
        data = response.json()
        assert data["email"] == "new@example.com"
        assert data["username"] == "newuser"
        assert "hashed_password" not in data

    def test_register_duplicate_email(self, client, test_user):
        response = client.post("/api/v1/auth/register", json={
            "email": test_user["email"],
            "username": "anotheruser",
            "password": "SecurePass1",
            "role": "staff"
        })
        assert response.status_code == 400

    def test_register_weak_password(self, client):
        response = client.post("/api/v1/auth/register", json={
            "email": "weak@example.com",
            "username": "weakuser",
            "password": "weak",
            "role": "staff"
        })
        assert response.status_code == 422

    def test_register_invalid_email(self, client):
        response = client.post("/api/v1/auth/register", json={
            "email": "not-an-email",
            "username": "bademail",
            "password": "SecurePass1",
            "role": "staff"
        })
        assert response.status_code == 422

    def test_register_invalid_role(self, client):
        response = client.post("/api/v1/auth/register", json={
            "email": "badrole@example.com",
            "username": "badrole",
            "password": "SecurePass1",
            "role": "superadmin"
        })
        assert response.status_code == 422

    def test_register_short_username(self, client):
        response = client.post("/api/v1/auth/register", json={
            "email": "short@example.com",
            "username": "ab",
            "password": "SecurePass1",
            "role": "staff"
        })
        assert response.status_code == 422


class TestAuthLogin:
    def test_login_success(self, client, test_user):
        response = client.post(
            "/api/v1/auth/token",
            data={"username": test_user["email"], "password": test_user["password"]}
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    def test_login_wrong_password(self, client, test_user):
        response = client.post(
            "/api/v1/auth/token",
            data={"username": test_user["email"], "password": "wrongpassword"}
        )
        assert response.status_code == 401

    def test_login_nonexistent_user(self, client):
        response = client.post(
            "/api/v1/auth/token",
            data={"username": "nobody@example.com", "password": "SecurePass1"}
        )
        assert response.status_code == 401


class TestAuthMe:
    def test_get_me(self, authorized_client):
        response = authorized_client.get("/api/v1/auth/me")
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "test@example.com"

    def test_get_me_unauthorized(self, client):
        response = client.get("/api/v1/auth/me")
        assert response.status_code == 401


class TestPasswordChange:
    def test_change_password(self, authorized_client, test_user):
        response = authorized_client.post("/api/v1/auth/change-password", json={
            "current_password": test_user["password"],
            "new_password": "NewSecurePass1"
        })
        assert response.status_code == 200

    def test_change_password_wrong_current(self, authorized_client):
        response = authorized_client.post("/api/v1/auth/change-password", json={
            "current_password": "wrongpassword",
            "new_password": "NewSecurePass1"
        })
        assert response.status_code == 400

    def test_change_password_weak_new(self, authorized_client, test_user):
        response = authorized_client.post("/api/v1/auth/change-password", json={
            "current_password": test_user["password"],
            "new_password": "weak"
        })
        assert response.status_code == 422


class TestDaycares:
    def test_create_daycare(self, authorized_client):
        response = authorized_client.post("/api/v1/daycares/", json={
            "name": "Sunshine Daycare",
            "address": "123 Main St",
            "phone": "555-1234",
            "email": "info@sunshine.com"
        })
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Sunshine Daycare"

    def test_list_daycares(self, authorized_client):
        authorized_client.post("/api/v1/daycares/", json={
            "name": "Test Daycare",
        })
        response = authorized_client.get("/api/v1/daycares/")
        assert response.status_code == 200
        assert len(response.json()) >= 1


class TestParents:
    def test_create_parent(self, authorized_client):
        response = authorized_client.post("/api/v1/parents/", json={
            "first_name": "John",
            "last_name": "Doe",
            "phone": "555-1234",
            "email": "john@example.com"
        })
        assert response.status_code == 201
        data = response.json()
        assert data["first_name"] == "John"

    def test_list_parents(self, authorized_client):
        response = authorized_client.get("/api/v1/parents/")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_delete_parent(self, authorized_client):
        create_resp = authorized_client.post("/api/v1/parents/", json={
            "first_name": "Jane",
            "last_name": "Smith",
            "phone": "555-5678"
        })
        parent_id = create_resp.json()["id"]
        response = authorized_client.delete(f"/api/v1/parents/{parent_id}")
        assert response.status_code == 200
        assert response.json()["message"] == "Parent deleted successfully"

        get_resp = authorized_client.get(f"/api/v1/parents/{parent_id}")
        assert get_resp.status_code == 404


class TestChildren:
    def test_create_child(self, authorized_client):
        response = authorized_client.post("/api/v1/children/", json={
            "first_name": "Baby",
            "last_name": "Doe",
            "date_of_birth": "2023-01-15T00:00:00",
            "allergies": "None"
        })
        assert response.status_code == 201
        data = response.json()
        assert data["first_name"] == "Baby"

    def test_list_children(self, authorized_client):
        response = authorized_client.get("/api/v1/children/")
        assert response.status_code == 200

    def test_delete_child(self, authorized_client):
        create_resp = authorized_client.post("/api/v1/children/", json={
            "first_name": "Toddler",
            "last_name": "Doe",
            "date_of_birth": "2022-06-01T00:00:00",
        })
        child_id = create_resp.json()["id"]
        response = authorized_client.delete(f"/api/v1/children/{child_id}")
        assert response.status_code == 200

        get_resp = authorized_client.get(f"/api/v1/children/{child_id}")
        assert get_resp.status_code == 404


class TestClasses:
    def test_create_class(self, authorized_client):
        response = authorized_client.post("/api/v1/classes/", json={
            "name": "Infants",
            "age_range": "0-12 months",
            "max_capacity": 10
        })
        assert response.status_code == 201

    def test_list_classes(self, authorized_client):
        response = authorized_client.get("/api/v1/classes/")
        assert response.status_code == 200

    def test_delete_class(self, authorized_client):
        create_resp = authorized_client.post("/api/v1/classes/", json={
            "name": "Toddlers",
            "age_range": "1-2 years",
        })
        class_id = create_resp.json()["id"]
        response = authorized_client.delete(f"/api/v1/classes/{class_id}")
        assert response.status_code == 200


class TestDashboard:
    def test_dashboard_stats(self, authorized_client):
        response = authorized_client.get("/api/v1/dashboard/stats")
        assert response.status_code == 200
        data = response.json()
        assert "total_children" in data
        assert "total_parents" in data
        assert "total_classes" in data
        assert "currently_present" in data
        assert "today_attendance" in data
        assert "today_incidents" in data


class TestOpenAPI:
    def test_docs_endpoint(self, client):
        response = client.get("/api/v1/docs")
        assert response.status_code == 200

    def test_openapi_json(self, client):
        response = client.get("/api/v1/openapi.json")
        assert response.status_code == 200
        data = response.json()
        assert "openapi" in data
        assert "info" in data
