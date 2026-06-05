from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api import auth, favorites, health, spice_routes, tags, uploads
from app.core.config import get_settings

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    Path(settings.image_storage_dir).mkdir(parents=True, exist_ok=True)
    yield


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    debug=settings.debug,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(spice_routes.router, prefix="/spice_routes", tags=["spice_routes"])
app.include_router(tags.router, prefix="/tags", tags=["tags"])
app.include_router(uploads.router, prefix="/spice_routes", tags=["uploads"])
app.include_router(favorites.router, tags=["favorites"])

app.mount(
    "/images",
    StaticFiles(directory=settings.image_storage_dir, check_dir=False),
    name="images",
)
