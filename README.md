# Daycare Manager

A comprehensive daycare management system built with FastAPI and SQLAlchemy. Manage children, parents, classes, attendance tracking, daily reports, and incident logging with role-based access control.

## Features

- **Authentication & Authorization**: JWT-based auth with role-based access control (admin/staff)
- **Child Management**: Full CRUD with parent associations, medical notes, and allergy tracking
- **Parent Management**: Contact info, emergency contacts, and linked children
- **Class Management**: Age ranges, capacity tracking, and teacher assignments
- **Attendance Tracking**: Sign-in/sign-out with staff tracking and daily summaries
- **Daily Reports**: Meals, naps, activities, mood, and diaper change logging
- **Incident Logging**: Severity tracking, action taken, and parent notification status
- **Dashboard Stats**: Real-time overview of children, attendance, and incidents
- **Soft Deletes**: Audit-friendly deletion for parents, children, and classes
- **Rate Limiting**: Protection against brute-force and API abuse
- **Input Validation**: Comprehensive Pydantic validation with sanitization
- **API Versioning**: `/api/v1/` prefixed routes for future compatibility
- **Auto-generated Docs**: OpenAPI/Swagger documentation at `/api/v1/docs`

## Prerequisites

- Python 3.12+
- PostgreSQL (for production) or SQLite (for development)
- Docker & Docker Compose (optional, for containerized deployment)

## Quick Start

### Local Development

1. **Clone the repository**

   ```bash
   git clone https://github.com/jvercher71/daycare-manager.git
   cd daycare-manager
   ```

2. **Create a virtual environment**

   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**

   ```bash
   cp .env.example .env
   # Edit .env with your configuration (especially SECRET_KEY)
   ```

5. **Run database migrations**

   ```bash
   alembic upgrade head
   ```

6. **Start the server**

   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

7. **Access the app**

   - API Docs: http://localhost:8000/api/v1/docs
   - Health Check: http://localhost:8000/health
   - Frontend: http://localhost:8000/

## Docker Deployment

### With SQLite (simple)

```bash
docker compose up --build
```

### With PostgreSQL (production)

```bash
# Update .env with DATABASE_URL=postgresql://daycare:daycare_password@db:5432/daycare_db
docker compose up --build
```

### Stop

```bash
docker compose down
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | Database connection string | `sqlite:///./daycare.db` |
| `SECRET_KEY` | JWT signing key (generate with `python -c "import secrets; print(secrets.token_urlsafe(32))"`) | Random (auto-generated) |
| `ALGORITHM` | JWT algorithm | `HS256` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Token TTL in minutes | `1440` (24 hours) |
| `ALLOWED_ORIGINS` | Comma-separated CORS origins | `*` |
| `ENVIRONMENT` | `development` or `production` | `development` |
| `RATE_LIMIT_MAX_REQUESTS` | Max requests per window | `10` |
| `RATE_LIMIT_WINDOW_SECONDS` | Rate limit window in seconds | `60` |
| `LOG_LEVEL` | Logging level | `INFO` |

## API Endpoints

### Authentication

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/auth/register` | Register a new user |
| POST | `/api/v1/auth/token` | Login and get JWT token |
| GET | `/api/v1/auth/me` | Get current user info |
| POST | `/api/v1/auth/change-password` | Change password |
| POST | `/api/v1/auth/reset-password-request` | Request password reset |
| POST | `/api/v1/auth/reset-password` | Confirm password reset |

### Daycares

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| POST | `/api/v1/daycares/` | Create daycare | Admin only |
| GET | `/api/v1/daycares/` | List all daycares | Authenticated |
| GET | `/api/v1/daycares/{id}` | Get daycare details | Authenticated |
| PUT | `/api/v1/daycares/{id}` | Update daycare | Admin only |

### Parents

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| POST | `/api/v1/parents/` | Create parent | Authenticated |
| GET | `/api/v1/parents/` | List parents (paginated) | Authenticated |
| GET | `/api/v1/parents/{id}` | Get parent details | Authenticated |
| PUT | `/api/v1/parents/{id}` | Update parent | Authenticated |
| DELETE | `/api/v1/parents/{id}` | Soft delete parent | Authenticated |

### Children

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| POST | `/api/v1/children/` | Create child | Authenticated |
| GET | `/api/v1/children/` | List children (paginated) | Authenticated |
| GET | `/api/v1/children/{id}` | Get child details | Authenticated |
| PUT | `/api/v1/children/{id}` | Update child | Authenticated |
| DELETE | `/api/v1/children/{id}` | Soft delete child | Authenticated |

### Classes

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| POST | `/api/v1/classes/` | Create class | Authenticated |
| GET | `/api/v1/classes/` | List classes (paginated) | Authenticated |
| GET | `/api/v1/classes/{id}` | Get class details | Authenticated |
| PUT | `/api/v1/classes/{id}` | Update class | Authenticated |
| DELETE | `/api/v1/classes/{id}` | Soft delete class | Authenticated |

### Attendance

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| POST | `/api/v1/attendance/signin` | Sign in a child | Authenticated |
| POST | `/api/v1/attendance/signout/{id}` | Sign out a child | Authenticated |
| GET | `/api/v1/attendance/today` | Get today's attendance | Authenticated |
| GET | `/api/v1/attendance/` | List attendance records | Authenticated |

### Daily Reports

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| POST | `/api/v1/daily-reports/` | Create daily report | Authenticated |
| GET | `/api/v1/daily-reports/` | List daily reports | Authenticated |

### Incidents

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| POST | `/api/v1/incidents/` | Create incident report | Authenticated |
| GET | `/api/v1/incidents/` | List incident reports | Authenticated |

### Dashboard

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| GET | `/api/v1/dashboard/stats` | Get dashboard statistics | Authenticated |

## Database Migrations

```bash
# Create a new migration
alembic revision --autogenerate -m "description of changes"

# Apply all pending migrations
alembic upgrade head

# Rollback one migration
alembic downgrade -1
```

## Running Tests

```bash
python -m pytest tests/ -v
```

## Project Structure

```
daycare-manager/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI app, middleware, router registration
│   ├── config.py            # Settings and environment configuration
│   ├── database.py          # SQLAlchemy engine and session management
│   ├── models.py            # Database models with soft delete support
│   ├── schemas.py           # Pydantic schemas with validation
│   ├── auth.py              # JWT authentication and password management
│   ├── middleware/
│   │   ├── __init__.py
│   │   └── rate_limiter.py  # Rate limiting middleware
│   └── routers/
│       ├── __init__.py
│       ├── auth.py          # Authentication endpoints
│       ├── daycares.py      # Daycare management
│       ├── parents.py       # Parent management
│       ├── children.py      # Child management
│       ├── classes.py       # Class management
│       ├── attendance.py    # Attendance tracking
│       ├── daily_reports.py # Daily report logging
│       ├── incidents.py     # Incident reporting
│       └── dashboard.py     # Dashboard statistics
├── alembic/                 # Database migrations
│   ├── env.py
│   └── versions/
├── alembic.ini
├── static/                  # Frontend assets
├── tests/                   # Test suite
│   └── test_api.py
├── Dockerfile
├── docker-compose.yml
├── vercel.json
├── requirements.txt
├── .env.example
└── .gitignore
```

## Security Features

- **JWT Authentication**: Secure token-based auth with configurable expiry
- **Password Hashing**: bcrypt with proper salt rounds
- **Password Validation**: Minimum 8 characters, requires uppercase, lowercase, and digit
- **Rate Limiting**: Separate limits for auth (5/min) and API (10/min) endpoints
- **Input Sanitization**: HTML escaping and XSS prevention on all text fields
- **Role-Based Access Control**: Admin vs staff permission levels
- **Soft Deletes**: Prevents accidental data loss with audit trails
- **CORS Configuration**: Configurable allowed origins
- **Environment-Based Secrets**: No hardcoded secrets, all config via environment variables

## License

MIT
