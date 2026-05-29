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


class TestBilling:
    @pytest_asyncio.fixture
    async def billing_client(self, client, db_session):
        from app.models import Daycare, User as UserModel, Child, Invoice, Payment
        from datetime import datetime
        # Clean slate for billing-related tables (only Users is cleared by `client`).
        for table in [Payment.__table__, Invoice.__table__, Child.__table__, Daycare.__table__]:
            await db_session.execute(table.delete())
        await db_session.commit()

        daycare = Daycare(name="Sprout Test Center")
        db_session.add(daycare)
        await db_session.commit()
        await db_session.refresh(daycare)

        user = UserModel(
            email="biller@example.com",
            username="biller",
            hashed_password=get_password_hash("TestPass123"),
            role="admin",
            is_active=True,
            daycare_id=daycare.id,
        )
        db_session.add(user)
        await db_session.commit()

        child = Child(
            first_name="Ava", last_name="Smith",
            date_of_birth=datetime(2022, 1, 1), daycare_id=daycare.id,
        )
        db_session.add(child)
        await db_session.commit()
        await db_session.refresh(child)

        resp = await client.post(
            "/api/v1/auth/token",
            data={"username": "biller@example.com", "password": "TestPass123"},
        )
        assert resp.status_code == 200, resp.json()
        client.headers = {"Authorization": f"Bearer {resp.json()['access_token']}"}
        return {"client": client, "child_id": child.id, "daycare_id": daycare.id}

    async def _create_invoice(self, c, **overrides):
        body = {"description": "May tuition", "amount": 50.00}
        body.update(overrides)
        return await c.post("/api/v1/billing/invoices", json=body)

    @pytest.mark.asyncio
    async def test_create_invoice_converts_dollars_to_cents(self, billing_client):
        c = billing_client["client"]
        r = await self._create_invoice(c, child_id=billing_client["child_id"])
        assert r.status_code == 201, r.json()
        data = r.json()
        assert data["amount_cents"] == 5000
        assert data["amount"] == 50.00
        assert data["balance"] == 50.00
        assert data["status"] == "draft"

    @pytest.mark.asyncio
    async def test_partial_then_full_payment_updates_status(self, billing_client):
        c = billing_client["client"]
        inv = (await self._create_invoice(c, status="sent")).json()
        inv_id = inv["id"]

        r1 = await c.post(f"/api/v1/billing/invoices/{inv_id}/payments", json={"amount": 20.00, "method": "cash"})
        assert r1.status_code == 201, r1.json()
        d1 = r1.json()
        assert d1["amount_paid"] == 20.00
        assert d1["balance"] == 30.00
        assert d1["status"] == "partial"

        r2 = await c.post(f"/api/v1/billing/invoices/{inv_id}/payments", json={"amount": 30.00, "method": "card"})
        assert r2.status_code == 201
        d2 = r2.json()
        assert d2["balance"] == 0.00
        assert d2["status"] == "paid"
        assert len(d2["payments"]) == 2

    @pytest.mark.asyncio
    async def test_overdue_status_is_computed_on_read(self, billing_client):
        c = billing_client["client"]
        inv = (await self._create_invoice(c, status="sent", due_date="2020-01-01T00:00:00")).json()
        r = await c.get("/api/v1/billing/invoices")
        assert r.status_code == 200
        match = [i for i in r.json() if i["id"] == inv["id"]]
        assert match and match[0]["status"] == "overdue"

    @pytest.mark.asyncio
    async def test_payment_must_be_positive(self, billing_client):
        c = billing_client["client"]
        inv = (await self._create_invoice(c)).json()
        r = await c.post(f"/api/v1/billing/invoices/{inv['id']}/payments", json={"amount": -5})
        assert r.status_code == 422

    @pytest.mark.asyncio
    async def test_cannot_pay_void_invoice(self, billing_client):
        c = billing_client["client"]
        inv = (await self._create_invoice(c)).json()
        await c.patch(f"/api/v1/billing/invoices/{inv['id']}", json={"status": "void"})
        r = await c.post(f"/api/v1/billing/invoices/{inv['id']}/payments", json={"amount": 10})
        assert r.status_code == 400

    @pytest.mark.asyncio
    async def test_summary_reflects_outstanding_and_collected(self, billing_client):
        c = billing_client["client"]
        inv = (await self._create_invoice(c, amount=100.00, status="sent")).json()
        await c.post(f"/api/v1/billing/invoices/{inv['id']}/payments", json={"amount": 40.00})
        r = await c.get("/api/v1/billing/summary")
        assert r.status_code == 200
        s = r.json()
        assert s["total_invoiced"] == 100.00
        assert s["outstanding"] == 60.00
        assert s["collected_this_month"] == 40.00

    @pytest.mark.asyncio
    async def test_missing_invoice_returns_404(self, billing_client):
        c = billing_client["client"]
        r = await c.get("/api/v1/billing/invoices/999999")
        assert r.status_code == 404

    @pytest.mark.asyncio
    async def test_invoice_rejects_child_from_other_daycare(self, billing_client, db_session):
        from app.models import Daycare, Child
        from datetime import datetime
        other = Daycare(name="Other Center")
        db_session.add(other)
        await db_session.commit()
        await db_session.refresh(other)
        other_child = Child(first_name="Zoe", last_name="Doe", date_of_birth=datetime(2021, 5, 5), daycare_id=other.id)
        db_session.add(other_child)
        await db_session.commit()
        await db_session.refresh(other_child)
        c = billing_client["client"]
        r = await self._create_invoice(c, child_id=other_child.id)
        assert r.status_code == 404
