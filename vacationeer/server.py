from __future__ import annotations

import json as _json
import logging
import os
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
from vacationeer.utils import slugify
from vacationeer.views.app_shell import generate_app
from vacationeer.views.overview import render_overview
from vacationeer.views.timeline import render_timeline

log = logging.getLogger("vacationeer")


# ---------------------------------------------------------------------------
# Rebuild helpers
# ---------------------------------------------------------------------------

def _render_tabs(trip: Trip) -> dict[str, str]:
    return {
        "overview-content": render_overview(trip),
        "timeline-content": render_timeline(trip),
    }


def _rebuild_all(trip: Trip, trip_path: Path, output_dir: Path) -> None:
    """Save trip JSON, regenerate map and app HTML."""
    save_trip(trip, trip_path)
    map_filename = f"{trip.dest_slug}-map.html"

    if trip.attractions:
        generate_map(trip, output_dir / map_filename)

    generate_app(trip, map_filename, output_dir / f"{trip.dest_slug}-app.html", tab_contents=_render_tabs(trip))


def _rebuild_app_only(trip: Trip, trip_path: Path, output_dir: Path) -> None:
    """Save trip JSON and regenerate app HTML (no map rebuild)."""
    save_trip(trip, trip_path)
    map_filename = f"{trip.dest_slug}-map.html"
    generate_app(trip, map_filename, output_dir / f"{trip.dest_slug}-app.html", tab_contents=_render_tabs(trip))


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


class ChatMessage(BaseModel):
    role: str  # "user" or "assistant"
    content: str


class ChatRequest(BaseModel):
    messages: list[ChatMessage]


def _build_chat_system_prompt(trip: Trip) -> str:
    """Build a system prompt that gives the AI context about the trip."""
    attractions_summary = ", ".join(a.name for a in trip.attractions[:15])
    if len(trip.attractions) > 15:
        attractions_summary += f" (and {len(trip.attractions) - 15} more)"

    day_trips_summary = ", ".join(dt.name for dt in trip.day_trips) if trip.day_trips else "none"

    days_summary = ""
    if trip.days:
        days_summary = f"\n\nScheduled days ({len(trip.days)}):"
        for d in trip.days[:10]:
            acts = ", ".join(a.name for a in d.activities) if d.activities else "empty"
            days_summary += f"\n- {d.date} ({d.label or 'no label'}): {acts}"

    prefs = ""
    if trip.preferences:
        p = trip.preferences
        prefs = f"\n\nPreferences: interests={p.interests}, avoid={p.avoid}, pace={p.pace}, daily_budget=€{p.daily_budget_eur or 'unset'}"

    return f"""You are a helpful travel planning assistant for the trip "{trip.name}" to {trip.destination}.
Trip dates: {trip.start_date} to {trip.end_date}, {trip.travelers} travelers, budget €{trip.budget_eur or 'unset'}.
{prefs}

Attractions ({len(trip.attractions)}): {attractions_summary}
Day trips: {day_trips_summary}
{days_summary}

You can suggest plans, answer questions about the destination, and help organize the itinerary.
Keep responses concise and practical. Use the traveler's context to personalize suggestions.
If the user asks to add an attraction or make a change, describe what you'd recommend — they can use the app UI to make the actual changes."""


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

def _scan_trips(project_root: Path) -> list[dict]:
    """Scan the trips/ directory and return metadata for each trip."""
    import json as _json

    trips_dir = project_root / "trips"
    result = []
    if not trips_dir.exists():
        return result

    for trip_dir in sorted(trips_dir.iterdir()):
        if not trip_dir.is_dir():
            continue
        slug = trip_dir.name
        entry: dict = {"slug": slug, "name": slug, "has_trip": False, "has_config": False}

        trip_json = trip_dir / "trip.json"
        config_json = trip_dir / "trip-config.json"

        if trip_json.exists():
            entry["has_trip"] = True
            try:
                data = _json.loads(trip_json.read_text(encoding="utf-8"))
                entry["name"] = data.get("name", slug)
                entry["destination"] = data.get("destination", "")
                dest_slug = entry["destination"].lower().replace(" ", "-")
                entry["app_url"] = f"/{dest_slug}-app.html"
            except Exception:
                pass
        elif config_json.exists():
            entry["has_config"] = True
            try:
                data = _json.loads(config_json.read_text(encoding="utf-8"))
                entry["name"] = data.get("name", slug)
                entry["destination"] = data.get("destination", "")
            except Exception:
                pass

        data_dir = project_root / "data" / slug
        entry["has_research"] = (data_dir / "attractions-and-activities.md").exists()

        result.append(entry)
    return result


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

    # Infer project root from trip path: trips/<slug>/trip.json -> project root
    project_root = trip_path.resolve().parent.parent.parent

    # In-memory trip state
    trip_state: dict[str, Trip] = {}

    @app.on_event("startup")
    def load_state() -> None:
        trip_state["trip"] = load_trip(trip_path)

    def _trip() -> Trip:
        return trip_state["trip"]

    # ------------------------------------------------------------------
    # Trip list endpoint (all trips)
    # ------------------------------------------------------------------

    @app.get("/api/trips")
    def list_trips():
        from vacationeer.pipeline.runner import get_job

        current_slug = trip_path.resolve().parent.name
        trips = _scan_trips(project_root)
        for t in trips:
            t["active"] = t["slug"] == current_slug
            job = get_job(t["slug"])
            if job:
                t["pipeline"] = job.to_dict()
        return trips

    # ------------------------------------------------------------------
    # Pipeline endpoints
    # ------------------------------------------------------------------

    class PipelineStart(BaseModel):
        destination: str
        name: Optional[str] = None
        start_date: str
        end_date: str
        dates_approximate: bool = False
        travelers: int = 2
        budget_eur: Optional[float] = None
        interests: list[str] = []
        avoid: list[str] = []
        pace: str = "moderate"
        budget_per_day_eur: Optional[float] = None
        context: Optional[str] = None
        must_do: Optional[str] = None
        accommodation_area: Optional[str] = None
        arrival_method: Optional[str] = None
        include_day_trips: bool = True
        light: bool = True

    @app.post("/api/pipeline/start", status_code=202)
    def start_pipeline(body: PipelineStart):
        from vacationeer.pipeline.runner import start_pipeline, get_job

        # Build slug
        import re as _re
        city = body.destination.split(",")[0].strip().lower()
        city_slug = _re.sub(r"[^a-z0-9]+", "-", city).strip("-")
        year_match = _re.search(r"20\d{2}", body.start_date)
        year = year_match.group() if year_match else "2026"
        slug = f"{city_slug}-{year}"

        # Check not already running
        existing = get_job(slug)
        if existing and existing.status in ("queued", "researching", "converting", "building"):
            return {"slug": slug, "status": existing.status, "message": "Pipeline already running"}

        config = {
            "id": slug,
            "name": body.name or f"{body.destination.split(',')[0].strip()} {year}",
            "destination": body.destination,
            "start_date": body.start_date,
            "end_date": body.end_date,
            "dates_approximate": body.dates_approximate,
            "travelers": body.travelers,
            "budget_eur": body.budget_eur,
            "preferences": {
                "interests": body.interests,
                "avoid": body.avoid,
                "pace": body.pace,
                "budget_per_day_eur": body.budget_per_day_eur,
            },
            "context": body.context,
            "must_do": body.must_do,
            "accommodation_area": body.accommodation_area,
            "arrival_method": body.arrival_method,
            "include_day_trips": body.include_day_trips,
        }

        job = start_pipeline(config, project_root, light=body.light, output_dir=output_dir)
        log.info("Started pipeline for %s", slug)
        return {"slug": slug, "status": job.status}

    @app.get("/api/pipeline/status/{slug}")
    def pipeline_status(slug: str):
        from vacationeer.pipeline.runner import get_job

        job = get_job(slug)
        if not job:
            raise HTTPException(status_code=404, detail=f"No pipeline job for '{slug}'")
        result = job.to_dict()
        # If done, include the app URL
        if job.status == "done":
            dest = job.config.get("destination", slug)
            dest_slug = dest.lower().replace(" ", "-").split(",")[0].strip()
            result["app_url"] = f"/{dest_slug}-app.html"
        return result

    @app.get("/api/pipeline/jobs")
    def pipeline_jobs():
        from vacationeer.pipeline.runner import list_jobs
        return list_jobs()

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

        slug_id = slugify(body.name)
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

        slug_id = slugify(body.name)
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
    # Chat endpoint
    # ------------------------------------------------------------------

    @app.post("/api/chat")
    async def chat(request: Request):
        trip = _trip()
        raw = await request.json()
        log.info("POST /api/chat")

        try:
            body = ChatRequest(**raw)
        except Exception as exc:
            raise HTTPException(status_code=422, detail=str(exc))

        # Check for Anthropic API key
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise HTTPException(
                status_code=503,
                detail="Chat requires ANTHROPIC_API_KEY environment variable to be set."
            )

        try:
            import anthropic
        except ImportError:
            raise HTTPException(
                status_code=503,
                detail="Chat requires the 'anthropic' package. Run: pip install anthropic"
            )

        system_prompt = _build_chat_system_prompt(trip)
        api_messages = [{"role": m.role, "content": m.content} for m in body.messages]

        try:
            client = anthropic.Anthropic()
            response = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=1024,
                system=system_prompt,
                messages=api_messages,
            )
            content = response.content[0].text
            log.info("Chat response: %s chars", len(content))
            return {"role": "assistant", "content": content}
        except Exception as exc:
            log.error("Chat API error: %s", exc)
            raise HTTPException(status_code=500, detail=f"AI error: {exc}")

    # ------------------------------------------------------------------
    # Static files (mounted last so API routes take priority)
    # ------------------------------------------------------------------

    output_dir.mkdir(parents=True, exist_ok=True)
    app.mount("/", StaticFiles(directory=str(output_dir), html=True), name="static")

    return app
