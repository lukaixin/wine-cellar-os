from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.core.database import init_db
from app.routers import (
    bottles,
    cellars,
    dashboard,
    exports,
    imports,
    import_batches,
    inventory_transactions,
    label_intake,
    locations,
    producers,
    vintages,
    winelist_import,
    wines,
)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    init_db()
    yield


settings = get_settings()
app = FastAPI(title=settings.app_name, lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(producers.router)
app.include_router(wines.router)
app.include_router(vintages.router)
app.include_router(cellars.router)
app.include_router(locations.router)
app.include_router(bottles.router)
app.include_router(inventory_transactions.router)
app.include_router(dashboard.router)
app.include_router(exports.router)
app.include_router(imports.router)
app.include_router(import_batches.router)
app.include_router(import_batches.api_router)
app.include_router(winelist_import.router)
app.include_router(label_intake.router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
