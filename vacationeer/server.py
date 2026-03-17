from __future__ import annotations

import re
from datetime import date
from pathlib import Path
from typing import Optional

from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from vacationeer.maps.generator import generate_map
from vacationeer.models.trip import (
    Attraction,
    Category,
    Day,
    Preferences,
    Trip,
)
from vacationeer.storage.json_store import load_trip, save_trip
from vacationeer.views.app_shell import generate_app
from vacationeer.views.chat import render_chat
from vacationeer.views.overview import render_overview
from vacationeer.views.timeline import render_timeline


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _slugify(name: str) -> str:
    """Convert a name to a URL-friendly slug id."""
    slug = name.lower().strip()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[\s_]+", "-", slug)
    slug = re.sub(r"-+", "-", slug).strip("-")
    return slug


# ---------------------------------------------------------------------------
# Rebuild helpers
# ---------------------------------------------------------------------------

def _rebuild_all(trip: Trip, trip_path: Path, output_dir: Path) -> None:
    """Save trip JSON, regenerate map and app HTML."""
    save_trip(trip, trip_path)
    dest_slug = trip.destination.lower().replace(" ", "-")
    map_filename = f"{dest_slug}-map.html"

    if trip.attractions:
        generate_map(trip, output_dir / map_filename)

    tab_contents = {
        "overview-content": render_overview(trip),
        "timeline-content": render_timeline(trip),
        "chat-content": render_chat(trip),
    }
    generate_app(trip, map_filename, output_dir / f"{dest_slug}-app.html", tab_contents=tab_contents)


def _rebuild_app_only(trip: Trip, trip_path: Path, output_dir: Path) -> None:
    """Save trip JSON and regenerate app HTML (no map rebuild)."""
    save_trip(trip, trip_path)
    dest_slug = trip.destination.lower().replace(" ", "-")
    map_filename = f"{dest_slug}-map.html"

    tab_contents = {
        "overview-content": render_overview(trip),
        "timeline-content": render_timeline(trip),
        "chat-content": render_chat(trip),
    }
    generate_app(trip, map_filename, output_dir / f"{dest_slug}-app.html", tab_contents=tab_contents)


# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------

class TripPatch(BaseModel):
    name: Optional[str] = None
    destination: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    travelers: Optional[int] = None
    budget_eur: Optional[float] = None


class ScoreBody(BaseModel):
    score: float


# ---------------------------------------------------------------------------
# App factory
# ---------------------------------------------------------------------------

def create_app(trip_path: Path, output_dir: Path) -> FastAPI:
    """Create and configure the FastAPI application."""

    app = FastAPI(title="Vacationeer API")

    # CORS - allow all origins for local dev
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # In-memory trip state
    trip_state: dict[str, Trip] = {}

    @app.on_event("startup")
    def load_state() -> None:
        trip_state["trip"] = load_trip(trip_path)

    def _trip() -> Trip:
        return trip_state["trip"]

    # ------------------------------------------------------------------
    # Trip endpoints
    # ------------------------------------------------------------------

    @app.get("/api/trip")
    def get_trip():
        return _trip()

    @app.patch("/api/trip")
    def patch_trip(patch: TripPatch, background_tasks: BackgroundTasks):
        trip = _trip()
        data = patch.model_dump(exclude_unset=True)
        for key, value in data.items():
            setattr(trip, key, value)
        background_tasks.add_task(_rebuild_all, trip, trip_path, output_dir)
        return trip

    # ------------------------------------------------------------------
    # Preferences endpoints
    # ------------------------------------------------------------------

    @app.get("/api/trip/preferences")
    def get_preferences():
        trip = _trip()
        return trip.preferences or Preferences()

    @app.put("/api/trip/preferences")
    def put_preferences(prefs: Preferences, background_tasks: BackgroundTasks):
        trip = _trip()
        trip.preferences = prefs
        background_tasks.add_task(_rebuild_app_only, trip, trip_path, output_dir)
        return trip.preferences

    # ------------------------------------------------------------------
    # Attraction endpoints
    # ------------------------------------------------------------------

    def _find_attraction(attraction_id: str) -> tuple[int, Attraction]:
        trip = _trip()
        for i, a in enumerate(trip.attractions):
            if a.id == attraction_id:
                return i, a
        raise HTTPException(status_code=404, detail=f"Attraction '{attraction_id}' not found")

    @app.get("/api/attractions")
    def list_attractions():
        return _trip().attractions

    @app.post("/api/attractions", status_code=201)
    def add_attraction(attraction: Attraction, background_tasks: BackgroundTasks):
        trip = _trip()
        # Auto-generate id from name if the default random id was used
        slug_id = _slugify(attraction.name)
        if slug_id:
            attraction.id = slug_id
        # Check for duplicate id
        existing_ids = {a.id for a in trip.attractions}
        if attraction.id in existing_ids:
            raise HTTPException(status_code=422, detail=f"Attraction with id '{attraction.id}' already exists")
        trip.attractions.append(attraction)
        background_tasks.add_task(_rebuild_all, trip, trip_path, output_dir)
        return attraction

    @app.get("/api/attractions/{attraction_id}")
    def get_attraction(attraction_id: str):
        _, attraction = _find_attraction(attraction_id)
        return attraction

    @app.patch("/api/attractions/{attraction_id}")
    def patch_attraction(attraction_id: str, updates: dict, background_tasks: BackgroundTasks):
        idx, attraction = _find_attraction(attraction_id)
        trip = _trip()
        for key, value in updates.items():
            if key == "id":
                continue  # don't allow id changes
            if hasattr(attraction, key):
                setattr(attraction, key, value)
        trip.attractions[idx] = attraction
        background_tasks.add_task(_rebuild_all, trip, trip_path, output_dir)
        return attraction

    @app.delete("/api/attractions/{attraction_id}")
    def delete_attraction(attraction_id: str, background_tasks: BackgroundTasks):
        idx, _ = _find_attraction(attraction_id)
        trip = _trip()
        trip.attractions.pop(idx)
        background_tasks.add_task(_rebuild_all, trip, trip_path, output_dir)
        return {"ok": True}

    @app.post("/api/attractions/{attraction_id}/score")
    def set_score(attraction_id: str, body: ScoreBody, background_tasks: BackgroundTasks):
        idx, attraction = _find_attraction(attraction_id)
        trip = _trip()
        attraction.user_score = body.score
        trip.attractions[idx] = attraction
        background_tasks.add_task(_rebuild_all, trip, trip_path, output_dir)
        return attraction

    # ------------------------------------------------------------------
    # Day endpoints
    # ------------------------------------------------------------------

    def _find_day(day_date: str) -> tuple[int, Day]:
        trip = _trip()
        for i, d in enumerate(trip.days):
            if str(d.date) == day_date:
                return i, d
        raise HTTPException(status_code=404, detail=f"Day '{day_date}' not found")

    @app.get("/api/days")
    def list_days():
        return _trip().days

    @app.post("/api/days", status_code=201)
    def add_day(day: Day, background_tasks: BackgroundTasks):
        trip = _trip()
        # Check for duplicate date
        existing_dates = {str(d.date) for d in trip.days}
        if str(day.date) in existing_dates:
            raise HTTPException(status_code=422, detail=f"Day '{day.date}' already exists")
        trip.days.append(day)
        trip.days.sort(key=lambda d: d.date)
        background_tasks.add_task(_rebuild_app_only, trip, trip_path, output_dir)
        return day

    @app.get("/api/days/{day_date}")
    def get_day(day_date: str):
        _, day = _find_day(day_date)
        return day

    @app.patch("/api/days/{day_date}")
    def patch_day(day_date: str, updates: dict, background_tasks: BackgroundTasks):
        idx, day = _find_day(day_date)
        trip = _trip()
        for key, value in updates.items():
            if key == "date":
                continue
            if hasattr(day, key):
                setattr(day, key, value)
        trip.days[idx] = day
        background_tasks.add_task(_rebuild_app_only, trip, trip_path, output_dir)
        return day

    @app.delete("/api/days/{day_date}")
    def delete_day(day_date: str, background_tasks: BackgroundTasks):
        idx, _ = _find_day(day_date)
        trip = _trip()
        trip.days.pop(idx)
        background_tasks.add_task(_rebuild_app_only, trip, trip_path, output_dir)
        return {"ok": True}

    # ------------------------------------------------------------------
    # Static files (mounted last so API routes take priority)
    # ------------------------------------------------------------------

    output_dir.mkdir(parents=True, exist_ok=True)
    app.mount("/", StaticFiles(directory=str(output_dir), html=True), name="static")

    return app
