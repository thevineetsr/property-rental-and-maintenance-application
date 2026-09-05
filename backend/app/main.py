from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.app.core.config import settings
from backend.app.api.auth import router as auth_router
from backend.app.api.units import router as units_router
from backend.app.api.rent import router as rent_router
from backend.app.api.maintenance import router as maintenance_router
from backend.app.api.dashboard import router as dashboard_router
from backend.app.db.base import Base
from backend.app.db.database import engine
from backend.app.seed import seed


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Auto-initialize database tables and seed demo data on server boot
    try:
        Base.metadata.create_all(bind=engine)
        seed()
    except Exception as e:
        print(f"[STARTUP WARNING] Database initialization: {e}")
    yield


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Production-grade Property Rental & Maintenance Management API with role-based access control and strict server-side lifecycle rules.",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# Enable CORS for Streamlit frontend and local testing
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API Routers
app.include_router(auth_router, prefix=settings.API_PREFIX)
app.include_router(units_router, prefix=settings.API_PREFIX)
app.include_router(rent_router, prefix=settings.API_PREFIX)
app.include_router(maintenance_router, prefix=settings.API_PREFIX)
app.include_router(dashboard_router, prefix=settings.API_PREFIX)


@app.get("/", tags=["System"])
def root():
    return {
        "project": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "status": "online",
        "docs": "/docs"
    }


@app.get("/health", tags=["System"])
def health_check():
    return {"status": "healthy"}
