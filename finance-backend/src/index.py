import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from dotenv import load_dotenv

from src.db.database import init_db
from src.routes.auth import router as auth_router
from src.routes.transactions import router as transactions_router
from src.routes.budgets import router as budgets_router

load_dotenv()

app = FastAPI(
    title="Finity Finance Tracker API",
    description="Personal finance tracker — transactions, budgets, analytics",
    version="1.0.0"
)

# ── CORS ───────────────────────────────────────────────────────────────
FRONTEND_URL = os.getenv("FRONTEND_URL", "*")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_URL] if FRONTEND_URL != "*" else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── API Routes ─────────────────────────────────────────────────────────
app.include_router(auth_router, prefix="/api")
app.include_router(transactions_router, prefix="/api")
app.include_router(budgets_router, prefix="/api")

# ── Serve frontend static files ────────────────────────────────────────
frontend_path = os.path.join(os.path.dirname(__file__), "..", "finance-frontend")
if os.path.exists(frontend_path):
    app.mount("/static", StaticFiles(directory=frontend_path), name="static")

    @app.get("/", include_in_schema=False)
    def serve_frontend():
        return FileResponse(os.path.join(frontend_path, "index.html"))

    @app.get("/{full_path:path}", include_in_schema=False)
    def serve_spa(full_path: str):
        file_path = os.path.join(frontend_path, full_path)
        if os.path.exists(file_path):
            return FileResponse(file_path)
        return FileResponse(os.path.join(frontend_path, "index.html"))

# ── Health check ───────────────────────────────────────────────────────
@app.get("/api/health", tags=["Health"])
def health():
    return {"status": "ok", "service": "Finity Finance API"}

# ── Startup ────────────────────────────────────────────────────────────
@app.on_event("startup")
def startup():
    init_db()
    print("Finity API started successfully.")
