from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv

from app.db import run_migrations
from app.routers import (
    accounts,
    analytics,
    budgets,
    card_import,
    cards,
    categories,
    conscious,
    goals,
    health,
    import_csv,
    insights,
    pluggy,
    planning,
    reminders,
    settings,
    transactions,
)
from app.security import SupabaseAuthMiddleware, router as security_router

load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    run_migrations()
    yield


app = FastAPI(title="FinPilot API", version="0.2.0", lifespan=lifespan)
static_dir = Path(__file__).resolve().parent / "static"
app.mount("/static", StaticFiles(directory=static_dir), name="static")
app.add_middleware(SupabaseAuthMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost",
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:8000",
        "http://127.0.0.1",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:8000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", include_in_schema=False)
def home():
    """Abre a interface disponível em vez de exibir uma página 404."""
    return RedirectResponse(url="/static/app.html", status_code=307)


app.include_router(security_router)
app.include_router(health.router)
app.include_router(categories.router)
app.include_router(accounts.router)
app.include_router(transactions.router)
app.include_router(budgets.router)
app.include_router(card_import.router)
app.include_router(cards.router)
app.include_router(goals.router)
app.include_router(reminders.router)
app.include_router(planning.router)
app.include_router(settings.router)
app.include_router(import_csv.router)
app.include_router(analytics.router)
app.include_router(insights.router)
app.include_router(pluggy.router)
app.include_router(conscious.router)
