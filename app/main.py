import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from app.database import engine, get_db, Base, init_db
from app.config import settings
from app.middleware.rate_limiter import rate_limit_middleware
from app.routers import auth, daycares, parents, children, classes, attendance, daily_reports, incidents, dashboard

logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("daycare_manager")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing database...")
    init_db()
    logger.info("Daycare Manager API started")
    yield
    logger.info("Shutting down...")


app = FastAPI(
    title="Daycare Manager API",
    version="2.0.0",
    description="A comprehensive daycare management system with attendance tracking, daily reports, incident logging, and parent communication.",
    docs_url="/api/v1/docs",
    openapi_url="/api/v1/openapi.json",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.middleware("http")(rate_limit_middleware)


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "An internal server error occurred"},
    )


@app.get("/")
async def root():
    return RedirectResponse(url="/static/index.html")


@app.get("/health")
async def health_check():
    return {"status": "healthy", "version": "2.0.0"}


app.include_router(auth.router, prefix="/api/v1")
app.include_router(daycares.router, prefix="/api/v1")
app.include_router(parents.router, prefix="/api/v1")
app.include_router(children.router, prefix="/api/v1")
app.include_router(classes.router, prefix="/api/v1")
app.include_router(attendance.router, prefix="/api/v1")
app.include_router(daily_reports.router, prefix="/api/v1")
app.include_router(incidents.router, prefix="/api/v1")
app.include_router(dashboard.router, prefix="/api/v1")

static_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "static")
if os.path.isdir(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
