from __future__ import annotations

import logging
import re
from datetime import date, time, timedelta
from pathlib import Path
from typing import Optional

from fastapi import BackgroundTasks, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from vacationeer.maps.generator import generate_map
from vacationeer.models.trip import (
    Attraction,
    Activity,
    Category,
    Day,
    DayTrip,
    Location,
    Preferences,
    TravelMode,
    Trip,
)
from vacationeer.storage.json_store import load_trip, save_trip
from vacationeer.views.app_shell import generate_app
from vacationeer.views.chat import render_chat
from vacationeer.views.overview import render_overview
from vacationeer.views.timeline import render_timeline

log = logging.getLogger("vacationeer")


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


class AttractionCreate(BaseModel):
    """Loose input model for creating attractions from the frontend."""
    name: str
    description: Optional[str] = None
    category: str = "landmark"
    lat: Optional[float] = None
    lng: Optional[float] = None
    address: Optional[str] = None
    price_eur: Optional[float] = None
    duration_minutes: Optional[int] = None
    tags: list[str] = []
    tips: Optional[str] = None
    url: Optional[str] = None
    expected_score: Optional[float] = None
    user_score: Optional[float] = None
    # Also accept nested location
    location: Optional[dict] = None


class ScoreBody(BaseModel):
    score: float


class DayTripCreate(BaseModel):
    """Loose input model for creating day trips from the frontend."""
    name: str
    destination: str
    description: Optional[str] = None
    lat: Optional[float] = None
    lng: Optional[float] = None
    location: Optional[dict] = None
    address: Optional[str] = None
    total_price_eur: Optional[float] = None
    total_duration_minutes: Optional[int] = None
    tags: list[str] = []
    tips: Optional[str] = None
    expected_score: Optional[float] = None
    user_score: Optional[float] = None


class ActivityCreate(BaseModel):
    """Loose input model for creating activities from the frontend."""
    name: str
    attraction_id: Optional[str] = None
    day_trip_id: Optional[str] = None
    start_time: Optional[str] = None  # "HH:MM" string
    duration_minutes: Optional[int] = None
    price_eur: Optional[float] = None
    category: Optional[str] = None
    notes: Optional[str] = None
    status: str = "planned"


class ScheduleBody(BaseModel):
    attraction_id: str
    date: date
    start_time: Optional[str] = None  # "HH:MM" string


def _parse_time(value: Optional[str]) -> Optional[time]:
    """Parse a 'HH:MM' string into a time object."""
    if not value:
        return None
    parts = value.strip().split(":")
    return time(int(parts[0]), int(parts[1]))


def _parse_category(value: Optional[str]) -> Optional[Category]:
    """Parse a string into a Category enum, returning None on failure."""
    if not value:
        return None
    try:
        return Category(value)
    except ValueError:
        return None


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
    async def add_attraction(request: Request, background_tasks: BackgroundTasks):
        trip = _trip()
        raw = await request.json()
        log.info("POST /api/attractions body: %s", raw)

        try:
            body = AttractionCreate(**raw)
        except Exception as exc:
            log.error("Validation error: %s", exc)
            raise HTTPException(status_code=422, detail=str(exc))

        # Build Location from flat lat/lng or nested location
        lat = lng = None
        address = body.address
        if body.location:
            lat = body.location.get("lat")
            lng = body.location.get("lng")
            address = address or body.location.get("address")
        if body.lat is not None:
            lat = body.lat
        if body.lng is not None:
            lng = body.lng

        if lat is None or lng is None:
            raise HTTPException(status_code=422, detail="Latitude and longitude are required")

        location = Location(lat=float(lat), lng=float(lng), address=address)

        # Parse category
        try:
            category = Category(body.category)
        except ValueError:
            category = Category.LANDMARK

        slug_id = _slugify(body.name)
        existing_ids = {a.id for a in trip.attractions}
        if slug_id in existing_ids:
            raise HTTPException(status_code=422, detail=f"Attraction with id '{slug_id}' already exists")

        attraction = Attraction(
            id=slug_id,
            name=body.name,
            description=body.description,
            location=location,
            category=category,
            price_eur=body.price_eur,
            duration_minutes=body.duration_minutes,
            tags=body.tags,
            tips=body.tips,
            url=body.url,
            expected_score=body.expected_score,
            user_score=body.user_score,
        )

        trip.attractions.append(attraction)
        background_tasks.add_task(_rebuild_all, trip, trip_path, output_dir)
        log.info("Added attraction: %s", attraction.id)
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
    # Day Trip endpoints
    # ------------------------------------------------------------------

    def _find_day_trip(day_trip_id: str) -> tuple[int, DayTrip]:
        trip = _trip()
        for i, dt in enumerate(trip.day_trips):
            if dt.id == day_trip_id:
                return i, dt
        raise HTTPException(status_code=404, detail=f"Day trip '{day_trip_id}' not found")

    @app.get("/api/day-trips")
    def list_day_trips():
        return _trip().day_trips

    @app.post("/api/day-trips", status_code=201)
    async def add_day_trip(request: Request, background_tasks: BackgroundTasks):
        trip = _trip()
        raw = await request.json()
        log.info("POST /api/day-trips body: %s", raw)

        try:
            body = DayTripCreate(**raw)
        except Exception as exc:
            log.error("Validation error: %s", exc)
            raise HTTPException(status_code=422, detail=str(exc))

        # Build Location from flat lat/lng or nested location
        lat = lng = None
        address = body.address
        if body.location:
            lat = body.location.get("lat")
            lng = body.location.get("lng")
            address = address or body.location.get("address")
        if body.lat is not None:
            lat = body.lat
        if body.lng is not None:
            lng = body.lng

        if lat is None or lng is None:
            raise HTTPException(status_code=422, detail="Latitude and longitude are required")

        location = Location(lat=float(lat), lng=float(lng), address=address)

        slug_id = _slugify(body.name)
        existing_ids = {dt.id for dt in trip.day_trips}
        if slug_id in existing_ids:
            raise HTTPException(status_code=422, detail=f"Day trip with id '{slug_id}' already exists")

        day_trip = DayTrip(
            id=slug_id,
            name=body.name,
            destination=body.destination,
            description=body.description,
            location=location,
            total_price_eur=body.total_price_eur,
            total_duration_minutes=body.total_duration_minutes,
            tags=body.tags,
            tips=body.tips,
            expected_score=body.expected_score,
            user_score=body.user_score,
        )

        trip.day_trips.append(day_trip)
        background_tasks.add_task(_rebuild_all, trip, trip_path, output_dir)
        log.info("Added day trip: %s", day_trip.id)
        return day_trip

    @app.get("/api/day-trips/{day_trip_id}")
    def get_day_trip(day_trip_id: str):
        _, day_trip = _find_day_trip(day_trip_id)
        return day_trip

    @app.patch("/api/day-trips/{day_trip_id}")
    def patch_day_trip(day_trip_id: str, updates: dict, background_tasks: BackgroundTasks):
        idx, day_trip = _find_day_trip(day_trip_id)
        trip = _trip()
        for key, value in updates.items():
            if key == "id":
                continue
            if hasattr(day_trip, key):
                setattr(day_trip, key, value)
        trip.day_trips[idx] = day_trip
        background_tasks.add_task(_rebuild_all, trip, trip_path, output_dir)
        log.info("Updated day trip: %s", day_trip.id)
        return day_trip

    @app.delete("/api/day-trips/{day_trip_id}")
    def delete_day_trip(day_trip_id: str, background_tasks: BackgroundTasks):
        idx, _ = _find_day_trip(day_trip_id)
        trip = _trip()
        trip.day_trips.pop(idx)
        background_tasks.add_task(_rebuild_all, trip, trip_path, output_dir)
        log.info("Deleted day trip: %s", day_trip_id)
        return {"ok": True}

    @app.post("/api/day-trips/{day_trip_id}/score")
    def set_day_trip_score(day_trip_id: str, body: ScoreBody, background_tasks: BackgroundTasks):
        idx, day_trip = _find_day_trip(day_trip_id)
        trip = _trip()
        day_trip.user_score = body.score
        trip.day_trips[idx] = day_trip
        background_tasks.add_task(_rebuild_all, trip, trip_path, output_dir)
        log.info("Set day trip score: %s = %s", day_trip_id, body.score)
        return day_trip

    # ------------------------------------------------------------------
    # Activity endpoints (nested under days)
    # ------------------------------------------------------------------

    @app.post("/api/days/{day_date}/activities", status_code=201)
    async def add_activity(day_date: str, request: Request, background_tasks: BackgroundTasks):
        idx, day = _find_day(day_date)
        trip = _trip()
        raw = await request.json()
        log.info("POST /api/days/%s/activities body: %s", day_date, raw)

        try:
            body = ActivityCreate(**raw)
        except Exception as exc:
            log.error("Validation error: %s", exc)
            raise HTTPException(status_code=422, detail=str(exc))

        activity = Activity(
            name=body.name,
            attraction_id=body.attraction_id,
            day_trip_id=body.day_trip_id,
            start_time=_parse_time(body.start_time),
            duration_minutes=body.duration_minutes,
            price_eur=body.price_eur,
            category=_parse_category(body.category),
            notes=body.notes,
            status=body.status,
        )

        day.activities.append(activity)
        trip.days[idx] = day
        background_tasks.add_task(_rebuild_app_only, trip, trip_path, output_dir)
        log.info("Added activity '%s' to day %s", activity.id, day_date)
        return activity

    @app.patch("/api/days/{day_date}/activities/{activity_id}")
    def patch_activity(day_date: str, activity_id: str, updates: dict, background_tasks: BackgroundTasks):
        day_idx, day = _find_day(day_date)
        trip = _trip()

        for i, act in enumerate(day.activities):
            if act.id == activity_id:
                for key, value in updates.items():
                    if key == "id":
                        continue
                    if key == "start_time" and isinstance(value, str):
                        value = _parse_time(value)
                    if key == "category" and isinstance(value, str):
                        value = _parse_category(value)
                    if hasattr(act, key):
                        setattr(act, key, value)
                day.activities[i] = act
                trip.days[day_idx] = day
                background_tasks.add_task(_rebuild_app_only, trip, trip_path, output_dir)
                log.info("Updated activity '%s' on day %s", activity_id, day_date)
                return act

        raise HTTPException(status_code=404, detail=f"Activity '{activity_id}' not found on day '{day_date}'")

    @app.delete("/api/days/{day_date}/activities/{activity_id}")
    def delete_activity(day_date: str, activity_id: str, background_tasks: BackgroundTasks):
        day_idx, day = _find_day(day_date)
        trip = _trip()

        for i, act in enumerate(day.activities):
            if act.id == activity_id:
                day.activities.pop(i)
                trip.days[day_idx] = day
                background_tasks.add_task(_rebuild_app_only, trip, trip_path, output_dir)
                log.info("Deleted activity '%s' from day %s", activity_id, day_date)
                return {"ok": True}

        raise HTTPException(status_code=404, detail=f"Activity '{activity_id}' not found on day '{day_date}'")

    # ------------------------------------------------------------------
    # Schedule endpoint
    # ------------------------------------------------------------------

    @app.post("/api/schedule", status_code=201)
    def schedule_attraction(body: ScheduleBody, background_tasks: BackgroundTasks):
        trip = _trip()
        log.info("POST /api/schedule body: attraction_id=%s date=%s start_time=%s",
                 body.attraction_id, body.date, body.start_time)

        # Find the attraction
        attraction: Optional[Attraction] = None
        for a in trip.attractions:
            if a.id == body.attraction_id:
                attraction = a
                break
        if attraction is None:
            raise HTTPException(status_code=404, detail=f"Attraction '{body.attraction_id}' not found")

        # Find or create the day
        day: Optional[Day] = None
        day_idx: Optional[int] = None
        for i, d in enumerate(trip.days):
            if d.date == body.date:
                day = d
                day_idx = i
                break

        if day is None:
            day = Day(date=body.date)
            trip.days.append(day)
            trip.days.sort(key=lambda d: d.date)
            # Find the index after sorting
            for i, d in enumerate(trip.days):
                if d.date == body.date:
                    day_idx = i
                    break

        # Create activity from attraction
        activity = Activity(
            name=attraction.name,
            attraction_id=attraction.id,
            start_time=_parse_time(body.start_time),
            duration_minutes=attraction.duration_minutes,
            price_eur=attraction.price_eur,
            category=attraction.category,
        )

        day.activities.append(activity)
        trip.days[day_idx] = day
        background_tasks.add_task(_rebuild_app_only, trip, trip_path, output_dir)
        log.info("Scheduled attraction '%s' on %s", attraction.id, body.date)
        return activity

    # ------------------------------------------------------------------
    # Init days endpoint
    # ------------------------------------------------------------------

    @app.post("/api/init-days", status_code=201)
    def init_days(background_tasks: BackgroundTasks):
        trip = _trip()
        log.info("POST /api/init-days for %s to %s", trip.start_date, trip.end_date)

        existing_dates = {d.date for d in trip.days}
        current = trip.start_date
        created = []
        while current <= trip.end_date:
            if current not in existing_dates:
                day = Day(date=current)
                trip.days.append(day)
                created.append(str(current))
            current += timedelta(days=1)

        trip.days.sort(key=lambda d: d.date)
        background_tasks.add_task(_rebuild_app_only, trip, trip_path, output_dir)
        log.info("Init days created %d new days: %s", len(created), created)
        return {"created": created, "total_days": len(trip.days)}

    # ------------------------------------------------------------------
    # Static files (mounted last so API routes take priority)
    # ------------------------------------------------------------------

    output_dir.mkdir(parents=True, exist_ok=True)
    app.mount("/", StaticFiles(directory=str(output_dir), html=True), name="static")

    return app
