import os
import sys
import time
from threading import Thread

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles


ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRONTEND_DIR = os.path.join(ROOT_DIR, "frontend")
LANDING_PAGE = os.path.join(FRONTEND_DIR, "p1.html")

if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from backend.base import keyword_index_collection, things_collection
from backend.routers.main_auth import auth_router
from backend.routers.main_borrow import borrow_router
from backend.routers.main_crud import crud_router
from backend.routers.main_devices import devices_router
from backend.routers.main_localisation import localisation_router
from backend.routers.main_notifications import notifications_router
from backend.routers.main_recherche import recherche_router


load_dotenv(os.path.join(ROOT_DIR, "bdd.env"))

index_mot_cle_collection = keyword_index_collection

app = FastAPI()


def _cleanup_orphan_keywords_on_startup():
    """Nettoie automatiquement les mots-cles orphelins au demarrage."""
    try:
        all_keyword_thing_ids = list(keyword_index_collection.distinct("thingId"))
        orphan_thing_ids = []

        for thing_id in all_keyword_thing_ids:
            thing_id_clean = str(thing_id).strip()
            if not things_collection.find_one({"id": thing_id_clean}):
                orphan_thing_ids.append(thing_id_clean)

        if orphan_thing_ids:
            result = keyword_index_collection.delete_many({"thingId": {"$in": orphan_thing_ids}})
            print(f"Cleanup startup: {result.deleted_count} orphan keywords removed")
    except Exception as exc:
        print(f"Cleanup startup error: {exc}")


def _initialize_view_counts_on_startup():
    """Initialise les compteurs de vues pour tous les objets existants."""
    try:
        result = things_collection.update_many(
            {"view_count": {"$exists": False}},
            {"$set": {"view_count": 0}},
        )
        if result.modified_count > 0:
            print(f"View count initialization: {result.modified_count} objects updated")
    except Exception as exc:
        print(f"View count initialization error: {exc}")


def _background_cleanup_task():
    """Nettoie les mots-cles orphelins periodiquement."""
    while True:
        try:
            time.sleep(300)

            all_keyword_thing_ids = list(keyword_index_collection.distinct("thingId"))
            orphan_thing_ids = []

            for thing_id in all_keyword_thing_ids:
                thing_id_clean = str(thing_id).strip()
                if not things_collection.find_one({"id": thing_id_clean}):
                    orphan_thing_ids.append(thing_id_clean)

            if orphan_thing_ids:
                result = keyword_index_collection.delete_many({"thingId": {"$in": orphan_thing_ids}})
                print(f"Periodic cleanup: {result.deleted_count} orphan keywords removed")
        except Exception as exc:
            print(f"Periodic cleanup error: {exc}")


def _normalize_origin(value: str) -> str:
    return str(value or "").strip().rstrip("/")


def _get_public_app_url() -> str:
    candidates = [
        os.getenv("PUBLIC_APP_URL"),
        os.getenv("APP_BASE_URL"),
        os.getenv("FRONTEND_PUBLIC_URL"),
    ]

    railway_public_domain = _normalize_origin(os.getenv("RAILWAY_PUBLIC_DOMAIN"))
    if railway_public_domain:
        if railway_public_domain.startswith(("http://", "https://")):
            candidates.append(railway_public_domain)
        else:
            candidates.append(f"https://{railway_public_domain}")

    for candidate in candidates:
        normalized = _normalize_origin(candidate)
        if normalized:
            return normalized

    return ""


def _get_origins() -> list[str]:
    origins = {
        "http://127.0.0.1:5500",
        "http://localhost:5500",
        "http://127.0.0.1:5501",
        "http://localhost:5501",
        "http://127.0.0.1:8000",
        "http://localhost:8000",
    }

    configured = os.getenv("FRONTEND_ORIGINS", "")
    for origin in configured.split(","):
        normalized = _normalize_origin(origin)
        if normalized:
            origins.add(normalized)

    public_app_url = _get_public_app_url()
    if public_app_url:
        origins.add(public_app_url)

    return sorted(origins)


app.add_middleware(
    CORSMiddleware,
    allow_origins=_get_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_cleanup_orphan_keywords_on_startup()
_initialize_view_counts_on_startup()

cleanup_thread = Thread(target=_background_cleanup_task, daemon=True)
cleanup_thread.start()

app.include_router(localisation_router)
app.include_router(recherche_router)
app.include_router(auth_router)
app.include_router(borrow_router)
app.include_router(crud_router)
app.include_router(notifications_router)
app.include_router(devices_router)


@app.get("/", include_in_schema=False)
def root():
    if os.path.exists(LANDING_PAGE):
        return FileResponse(LANDING_PAGE, media_type="text/html")

    fallback_index = os.path.join(FRONTEND_DIR, "index.html")
    if os.path.exists(fallback_index):
        return FileResponse(fallback_index, media_type="text/html")

    return {"message": "API is running"}


@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "frontend_dir_exists": os.path.isdir(FRONTEND_DIR),
    }


if os.path.isdir(FRONTEND_DIR):
    app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
