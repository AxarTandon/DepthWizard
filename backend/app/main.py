from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.core.database import Base, engine
from app.api.v1.router import api_router

# Import all models so Base.metadata knows about every table before create_all.
from app.models import user, project, processing, calibration, validation, alert, chat  # noqa: F401

settings = get_settings()

app = FastAPI(title="Depthwizard API", version="1.0.0")

cors_origins = list(
    dict.fromkeys(
        [
            "http://localhost:3000",
            "http://localhost:3001",
            "http://127.0.0.1:3000",
            "http://127.0.0.1:3001",
            "https://depthwizard-one.vercel.app",
            *settings.cors_origins_list,
        ]
    )
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$|^https://[\w\-]+\.vercel\.app$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

@app.get("/")
@app.head("/")
def root():
    return {
        "app": "DepthWizard API",
        "status": "online",
        "version": "1.0.0",
        "docs": "/docs",
        "api_v1": "/api/v1"
    }

@app.get("/health")
@app.head("/health")
def health():
    return {"status": "ok", "app": "DepthWizard"}

# Mount both with /api/v1 prefix and at root for full frontend compatibility
app.include_router(api_router, prefix="/api/v1")
app.include_router(api_router)


@app.on_event("startup")
def on_startup():
    # For a hackathon-scale deployment, create_all is fine. Switch to Alembic
    # migrations (already scaffolded in /alembic) once the schema stabilizes.
    Base.metadata.create_all(bind=engine)

    # Seed default demo user if not present
    from app.core.database import SessionLocal
    from app.models.user import User
    from app.core.security import hash_password

    db = SessionLocal()
    try:
        if not db.query(User).filter(User.email == "demo@depthwizard.com").first():
            demo_user = User(
                name="Demo User",
                email="demo@depthwizard.com",
                password_hash=hash_password("demo12345"),
                organization="DepthWizard Demo",
            )
            db.add(demo_user)
            db.commit()
    finally:
        db.close()

