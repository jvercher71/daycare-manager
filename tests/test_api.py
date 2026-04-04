import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from app.database import Base, get_db
from app.main import app
from app.models import User
from app.auth import get_password_hash

SQLALCHEMY_DATABASE_URL = "sqlite+aiosqlite:///./test_daycare.db"

engine = create_async_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = async_sessionmaker(
    bind=engine, expire_on_commit=False, class_=AsyncSession
)


async def override_get_db():
    async with TestingSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


app.dependency_overrides[get_db] = override_get_db


@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_database():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def client():
    async with TestingSessionLocal() as db:
        await db.execute(User.__table__.delete())
        await db.commit()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture
async def db_session():
    async with TestingSessionLocal() as session:
        yield session


@pytest_asyncio.fixture
async def test_user(db_session):
    user = User(
        email="test@example.com",
        username="testuser",
        hashed_password=get_password_hash("TestPass123"),
        role="admin",
        is_active=True
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return {
        "id": user.id,
        "email": user.email,
        "username": user.username,
        "password": "TestPass123",
        "role": user.role
    }


@pytest_asyncio.fixture
async def auth_token(client, test_user):
    response = await client.post(
        "/api/v1/auth/token",
        data={"username": test_user["email"], "password": test_user["password"]}
    )
    assert response.status_code == 200, f"Login failed: {response.json()}"
    return response.json()["access_token"]


@pytest_asyncio.fixture
async def authorized_client(client, auth_token):
    client.headers = {"Authorization": f"Bearer {auth_token}"}
    return client


class TestHealthEndpoint:
    @pytest.mark.asyncio
    async def test_health_check(self, client):
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data


class TestAuthRegistration:
    @pytest.mark.asyncio
    async def test_register_success(self, client):
        response = await client.post("/api/v1/auth/register", json={
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

    @pytest.mark.asyncio
    async def test_register_duplicate_email(self, client, test_user):
        response = await client.post("/api/v1/auth/register", json={
            "email": test_user["email"],
            "username": "anotheruser",
            "password": "SecurePass1",
            "role": "staff"
        })
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_register_weak_password(self, client):
        response = await client.post("/api/v1/auth/register", json={
            "email": "weak@example.com",
            "username": "weakuser",
            "password": "weak",
            "role": "staff"
        })
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_register_invalid_email(self, client):
        response = await client.post("/api/v1/auth/register", json={
            "email": "not-an-email",
            "username": "bademail",
            "password": "SecurePass1",
            "role": "staff"
        })
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_register_invalid_role(self, client):
        response = await client.post("/api/v1/auth/register", json={
            "email": "badrole@example.com",
            "username": "badrole",
            "password": "SecurePass1",
            "role": "superadmin"
        })
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_register_short_username(self, client):
        response = await client.post("/api/v1/auth/register", json={
            "email": "short@example.com",
            "username": "ab",
            "password": "SecurePass1",
            "role": "staff"
        })
        assert response.status_code == 422


class TestAuthLogin:
    @pytest.mark.asyncio
    async def test_login_success(self, client, test_user):
        response = await client.post(
            "/api/v1/auth/token",
            data={"username": test_user["email"], "password": test_user["password"]}
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    @pytest.mark.asyncio
    async def test_login_wrong_password(self, client, test_user):
        response = await client.post(
            "/api/v1/auth/token",
            data={"username": test_user["email"], "password": "wrongpassword"}
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_login_nonexistent_user(self, client):
        response = await client.post(
            "/api/v1/auth/token",
            data={"username": "nobody@example.com", "password": "SecurePass1"}
        )
        assert response.status_code == 401


class TestAuthMe:
    @pytest.mark.asyncio
    async def test_get_me(self, authorized_client):
        response = await authorized_client.get("/api/v1/auth/me")
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "test@example.com"

    @pytest.mark.asyncio
    async def test_get_me_unauthorized(self, client):
        response = await client.get("/api/v1/auth/me")
        assert response.status_code == 401


class TestPasswordChange:
    @pytest.mark.asyncio
    async def test_change_password(self, authorized_client, test_user):
        response = await authorized_client.post("/api/v1/auth/change-password", json={
            "current_password": test_user["password"],
            "new_password": "NewSecurePass1"
        })
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_change_password_wrong_current(self, authorized_client):
        response = await authorized_client.post("/api/v1/auth/change-password", json={
            "current_password": "wrongpassword",
            "new_password": "NewSecurePass1"
        })
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_change_password_weak_new(self, authorized_client, test_user):
        response = await authorized_client.post("/api/v1/auth/change-password", json={
            "current_password": test_user["password"],
            "new_password": "weak"
        })
        assert response.status_code == 422


class TestDaycares:
    @pytest.mark.asyncio
    async def test_create_daycare(self, authorized_client):
        response = await authorized_client.post("/api/v1/daycares/", json={
            "name": "Sunshine Daycare",
            "address": "123 Main St",
            "phone": "555-1234",
            "email": "info@sunshine.com"
        })
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Sunshine Daycare"

    @pytest.mark.asyncio
    async def test_list_daycares(self, authorized_client):
        await authorized_client.post("/api/v1/daycares/", json={"name": "Test Daycare"})
        response = await authorized_client.get("/api/v1/daycares/")
        assert response.status_code == 200
        assert len(response.json()["items"]) >= 1


class TestParents:
    @pytest.mark.asyncio
    async def test_create_parent(self, authorized_client):
        response = await authorized_client.post("/api/v1/parents/", json={
            "first_name": "John",
            "last_name": "Doe",
            "phone": "555-1234",
            "email": "john@example.com"
        })
        assert response.status_code == 201
        data = response.json()
        assert data["first_name"] == "John"

    @pytest.mark.asyncio
    async def test_list_parents(self, authorized_client):
        response = await authorized_client.get("/api/v1/parents/")
        assert response.status_code == 200
        assert isinstance(response.json()["items"], list)

    @pytest.mark.asyncio
    async def test_delete_parent(self, authorized_client):
        create_resp = await authorized_client.post("/api/v1/parents/", json={
            "first_name": "Jane",
            "last_name": "Smith",
            "phone": "555-5678"
        })
        parent_id = create_resp.json()["id"]
        response = await authorized_client.delete(f"/api/v1/parents/{parent_id}")
        assert response.status_code == 200
        assert response.json()["message"] == "Parent deleted successfully"

        get_resp = await authorized_client.get(f"/api/v1/parents/{parent_id}")
        assert get_resp.status_code == 404


class TestChildren:
    @pytest.mark.asyncio
    async def test_create_child(self, authorized_client):
        response = await authorized_client.post("/api/v1/children/", json={
            "first_name": "Baby",
            "last_name": "Doe",
            "date_of_birth": "2023-01-15T00:00:00",
            "allergies": "None"
        })
        assert response.status_code == 201
        data = response.json()
        assert data["first_name"] == "Baby"

    @pytest.mark.asyncio
    async def test_list_children(self, authorized_client):
        response = await authorized_client.get("/api/v1/children/")
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_delete_child(self, authorized_client):
        create_resp = await authorized_client.post("/api/v1/children/", json={
            "first_name": "Toddler",
            "last_name": "Doe",
            "date_of_birth": "2022-06-01T00:00:00",
        })
        child_id = create_resp.json()["id"]
        response = await authorized_client.delete(f"/api/v1/children/{child_id}")
        assert response.status_code == 200

        get_resp = await authorized_client.get(f"/api/v1/children/{child_id}")
        assert get_resp.status_code == 404


class TestClasses:
    @pytest.mark.asyncio
    async def test_create_class(self, authorized_client):
        response = await authorized_client.post("/api/v1/classes/", json={
            "name": "Infants",
            "age_range": "0-12 months",
            "max_capacity": 10
        })
        assert response.status_code == 201

    @pytest.mark.asyncio
    async def test_list_classes(self, authorized_client):
        response = await authorized_client.get("/api/v1/classes/")
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_delete_class(self, authorized_client):
        create_resp = await authorized_client.post("/api/v1/classes/", json={
            "name": "Toddlers",
            "age_range": "1-2 years",
        })
        class_id = create_resp.json()["id"]
        response = await authorized_client.delete(f"/api/v1/classes/{class_id}")
        assert response.status_code == 200


class TestDashboard:
    @pytest.mark.asyncio
    async def test_dashboard_stats(self, authorized_client):
        response = await authorized_client.get("/api/v1/dashboard/stats")
        assert response.status_code == 200
        data = response.json()
        assert "total_children" in data
        assert "total_parents" in data
        assert "total_classes" in data
        assert "currently_present" in data
        assert "today_attendance" in data
        assert "today_incidents" in data


class TestOpenAPI:
    @pytest.mark.asyncio
    async def test_docs_endpoint(self, client):
        response = await client.get("/api/v1/docs")
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_openapi_json(self, client):
        response = await client.get("/api/v1/openapi.json")
        assert response.status_code == 200
        data = response.json()
        assert "openapi" in data
        assert "info" in data
