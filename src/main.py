from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.core.config import settings
from src.api.routes import tours, bookings, analytics, contact, admin_auth
from src.database.database import SessionLocal
from src.models import models, admin  # noqa: F401  (register tables)
from src.services.admin_bootstrap import run_startup_sync



@asynccontextmanager
async def lifespan(app: FastAPI):
    run_startup_sync(app.state.session_factory)
    yield


app = FastAPI(
    lifespan=lifespan,
    title="Afro Nyanka Tours API",
    description="Backend API for Afro Nyanka Tours booking system",
    version="1.0.0"
)

app.state.session_factory = SessionLocal

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(tours.router, prefix="/api/tours", tags=["tours"])
app.include_router(bookings.router, prefix="/api/bookings", tags=["bookings"])
app.include_router(analytics.router, prefix="/api/analytics", tags=["analytics"])
app.include_router(contact.router, prefix="/api/contact", tags=["contact"])
app.include_router(admin_auth.router, prefix="/api/admin/auth", tags=["admin-auth"])

@app.get("/")
async def root():
    return {"message": "Welcome to Afro Nyanka Tours API"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}
