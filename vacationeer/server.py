from __future__ import annotations

import json as _json
import logging
import re
from datetime import date, time, timedelta
from pathlib import Path
from typing import Optional
from uuid import uuid4

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
    Grouping,
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


class SwapDaysBody(BaseModel):
    date1: str
    date2: str


class MoveActivityBody(BaseModel):
    activity_id: str
    target_date: str


class AIPlanBody(BaseModel):
    prompt: str


class ChatMessage(BaseModel):
    role: str  # "user" or "assistant"
    content: str


class ChatRequest(BaseModel):
    messages: list[ChatMessage]


def _build_chat_system_prompt(trip: Trip) -> str:
    """Short system prompt with tool descriptions. Data fetched on demand."""
    return (
        f'Travel assistant for "{trip.name}" to {trip.destination}. '
        f'{trip.start_date} to {trip.end_date}, {trip.travelers} travelers.\n'
        f'Be very concise — short sentences, no filler. Use markdown for lists.\n\n'
        f'You have tools. To use one, put the tag on its own line in your response.\n'
        f'DATA TOOLS (read-only, you get data back and then answer):\n'
        f'<<GET_ATTRACTIONS>> — list all attractions\n'
        f'<<GET_SCHEDULE>> — day-by-day schedule\n'
        f'<<GET_DAY_TRIPS>> — day trips with sub-attractions\n'
        f'<<GET_UNSCHEDULED>> — unscheduled attractions\n\n'
        f'ACTION TOOLS (modify the trip — include your text response too):\n'
        f'<<SCHEDULE:attraction name:YYYY-MM-DD:HH:MM>> — schedule an attraction to a day\n'
        f'<<UNSCHEDULE:attraction name:YYYY-MM-DD>> — remove from a day\n'
        f'Example: <<SCHEDULE:Bioparc:2026-03-24:10:00>>\n\n'
        f'After using a data tool, answer concisely. Action tools are executed automatically.'
    )


def _resolve_tool_call(tag: str, trip: Trip) -> str | None:
    """Resolve a data tool tag into trip data text."""
    if tag == "GET_ATTRACTIONS":
        lines = []
        for a in trip.attractions:
            parts = [a.name, a.category.value]
            if a.price_eur is not None:
                parts.append(f"EUR {a.price_eur}")
            if a.duration_minutes:
                parts.append(f"{a.duration_minutes}min")
            if a.user_score is not None:
                parts.append(f"rated {a.user_score}/10")
            if a.tags:
                parts.append(f"tags: {', '.join(a.tags)}")
            lines.append(" | ".join(parts))
        return f"Attractions ({len(trip.attractions)}):\n" + "\n".join(lines)

    if tag == "GET_SCHEDULE":
        lines = []
        for day in trip.days:
            acts = ", ".join(
                f"{a.name} ({a.start_time.strftime('%H:%M') if a.start_time else '?'})"
                for a in day.activities
            ) if day.activities else "empty"
            label = f" ({day.label})" if day.label else ""
            lines.append(f"{day.date}{label}: {acts}")
        return "Schedule:\n" + "\n".join(lines) if lines else "No days scheduled yet."

    if tag == "GET_DAY_TRIPS":
        lines = []
        for dt in trip.day_trips:
            subs = ", ".join(s.name for s in dt.sub_attractions)
            parts = [dt.name, f"to {dt.destination}"]
            if dt.total_price_eur is not None:
                parts.append(f"EUR {dt.total_price_eur}")
            if dt.total_duration_minutes:
                parts.append(f"{dt.total_duration_minutes}min")
            if subs:
                parts.append(f"includes: {subs}")
            if dt.tips:
                parts.append(f"tips: {dt.tips}")
            lines.append(" | ".join(parts))
        return f"Day trips ({len(trip.day_trips)}):\n" + "\n".join(lines) if lines else "No day trips."

    if tag == "GET_UNSCHEDULED":
        scheduled_ids = set()
        for day in trip.days:
            for act in day.activities:
                if act.attraction_id:
                    scheduled_ids.add(act.attraction_id)
        unscheduled = [a.name for a in trip.attractions if a.id not in scheduled_ids]
        return f"Unscheduled ({len(unscheduled)}):\n" + "\n".join(unscheduled) if unscheduled else "All attractions are scheduled."

    return None


def _find_attraction_by_name(trip: Trip, name: str) -> Attraction | None:
    """Fuzzy-match an attraction by name (case-insensitive substring)."""
    name_lower = name.lower().strip()
    # Exact match first
    for a in trip.attractions:
        if a.name.lower() == name_lower:
            return a
    # Substring match
    for a in trip.attractions:
        if name_lower in a.name.lower() or a.name.lower() in name_lower:
            return a
    return None


def _execute_action_tag(tag_content: str, trip: Trip, trip_path: Path, output_dir: Path) -> str | None:
    """Execute an action tag and return a status message."""
    # Split carefully: ACTION:name:YYYY-MM-DD:HH:MM
    # Name may contain colons (unlikely), time is HH:MM (two parts)
    parts = tag_content.split(":")
    action = parts[0]

    if action == "SCHEDULE" and len(parts) >= 3:
        attr_name = parts[1].strip()
        date_str = parts[2].strip()
        # Time is HH:MM which splits into two parts
        time_str = f"{parts[3]}:{parts[4]}" if len(parts) > 4 else (parts[3].strip() if len(parts) > 3 else None)
        attraction = _find_attraction_by_name(trip, attr_name)
        if not attraction:
            return f"Could not find attraction '{attr_name}'"
        try:
            from datetime import date as _date, time as _time
            d = _date.fromisoformat(date_str)
            # Find or create day
            day = None
            for existing in trip.days:
                if existing.date == d:
                    day = existing
                    break
            if day is None:
                day = Day(date=d)
                trip.days.append(day)
                trip.days.sort(key=lambda x: x.date)
            # Check not already scheduled there
            for act in day.activities:
                if act.attraction_id == attraction.id:
                    return f"'{attraction.name}' is already on {date_str}"
            start = None
            if time_str:
                h, m = time_str.split(":")
                start = _time(int(h), int(m))
            activity = Activity(
                attraction_id=attraction.id,
                name=attraction.name,
                start_time=start,
                duration_minutes=attraction.duration_minutes,
                price_eur=attraction.price_eur,
                category=attraction.category,
            )
            day.activities.append(activity)
            save_trip(trip, trip_path)
            _rebuild_all(trip, trip_path, output_dir)
            return f"Scheduled '{attraction.name}' on {date_str}" + (f" at {time_str}" if time_str else "")
        except Exception as e:
            return f"Failed to schedule: {e}"

    if action == "UNSCHEDULE" and len(parts) >= 3:
        attr_name = parts[1].strip()
        date_str = parts[2].strip()
        attraction = _find_attraction_by_name(trip, attr_name)
        if not attraction:
            return f"Could not find attraction '{attr_name}'"
        try:
            from datetime import date as _date
            d = _date.fromisoformat(date_str)
            for day in trip.days:
                if day.date == d:
                    before = len(day.activities)
                    day.activities = [a for a in day.activities if a.attraction_id != attraction.id]
                    if len(day.activities) < before:
                        save_trip(trip, trip_path)
                        _rebuild_all(trip, trip_path, output_dir)
                        return f"Removed '{attraction.name}' from {date_str}"
            return f"'{attraction.name}' not found on {date_str}"
        except Exception as e:
            return f"Failed to unschedule: {e}"

    return None


def _format_chat_messages(messages: list) -> str:
    """Format multi-turn chat messages into a single prompt for stateless providers."""
    parts = []
    for m in messages:
        label = "User" if m.role == "user" else "Assistant"
        parts.append(f"{label}: {m.content}")
    return "\n\n".join(parts)


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

    # --- Static day routes BEFORE parameterized {day_date} ---

    @app.post("/api/days/swap")
    def swap_days(body: SwapDaysBody, background_tasks: BackgroundTasks):
        from vacationeer.planning.scheduler import swap_days as _swap_days
        trip = _trip()
        d1 = date.fromisoformat(body.date1)
        d2 = date.fromisoformat(body.date2)
        trip = _swap_days(trip, d1, d2)
        background_tasks.add_task(_rebuild_all, trip, trip_path, output_dir)
        return {"ok": True}

    @app.post("/api/activities/move")
    def move_activity(body: MoveActivityBody, background_tasks: BackgroundTasks):
        from vacationeer.planning.scheduler import move_activity as _move_activity
        trip = _trip()
        target = date.fromisoformat(body.target_date)
        trip = _move_activity(trip, body.activity_id, target)
        background_tasks.add_task(_rebuild_all, trip, trip_path, output_dir)
        return {"ok": True}

    @app.post("/api/days/{day_date}/ai-plan")
    def ai_plan_day(day_date: str, body: AIPlanBody, background_tasks: BackgroundTasks):
        from vacationeer.models.trip import Activity, Category as Cat
        from vacationeer.pipeline.ai_provider import get_provider
        trip = _trip()
        idx, day = _find_day(day_date)

        # Build list of unscheduled attractions
        scheduled_ids = set()
        for d in trip.days:
            for act in d.activities:
                if act.attraction_id:
                    scheduled_ids.add(act.attraction_id)
        unscheduled = [a for a in trip.attractions if a.id not in scheduled_ids]

        if not unscheduled:
            raise HTTPException(400, "No unscheduled attractions available")

        attr_list = "\n".join(
            f"- {a.id}: {a.name} ({a.duration_minutes or '?'}min, {a.category.value}, "
            f"{'Free' if a.price_eur == 0 else ('€' + str(a.price_eur)) if a.price_eur else '?'}"
            f"{', score ' + str(a.expected_score) if a.expected_score else ''})"
            for a in unscheduled
        )
        prompt = (
            f"Plan activities for {day_date} ({day.label or 'no label'}). "
            f"User request: \"{body.prompt}\"\n\n"
            f"Available unscheduled attractions:\n{attr_list}\n\n"
            f"Return ONLY a JSON array, no other text:\n"
            f'[{{"attraction_id": "...", "start_time": "HH:MM", "notes": "..."}}, ...]\n'
            f"Pick attractions that fit the user's description. Order by start_time. "
            f"For custom activities (not in the list), use: "
            f'{{"name": "...", "start_time": "HH:MM", "duration_minutes": N, "category": "food|entertainment|...", "notes": "..."}}'
        )

        try:
            provider = get_provider()
            response = provider.complete(prompt, system="You are a travel planner. Return only valid JSON.")
            # Extract JSON array from response
            import json as _json
            text = response.strip()
            start = text.find("[")
            end = text.rfind("]") + 1
            if start < 0 or end <= start:
                raise ValueError("No JSON array found in AI response")
            items = _json.loads(text[start:end])
        except Exception as e:
            raise HTTPException(503, f"AI planning failed: {e}")

        # Create activities from AI response
        attr_map = {a.id: a for a in trip.attractions}
        for item in items:
            aid = item.get("attraction_id")
            if aid and aid in attr_map:
                a = attr_map[aid]
                act = Activity(
                    attraction_id=aid,
                    name=a.name,
                    start_time=item.get("start_time"),
                    duration_minutes=a.duration_minutes,
                    price_eur=a.price_eur,
                    category=a.category,
                    notes=item.get("notes"),
                )
            else:
                cat_str = item.get("category", "entertainment")
                try:
                    cat = Cat(cat_str)
                except ValueError:
                    cat = Cat.ENTERTAINMENT
                act = Activity(
                    name=item.get("name", "Activity"),
                    start_time=item.get("start_time"),
                    duration_minutes=item.get("duration_minutes", 60),
                    category=cat,
                    notes=item.get("notes"),
                )
            day.activities.append(act)

        trip.days[idx] = day
        background_tasks.add_task(_rebuild_all, trip, trip_path, output_dir)
        return day

    # --- Parameterized day routes ---

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
    # Grouping endpoints
    # ------------------------------------------------------------------

    def _find_grouping(gid: str):
        trip = _trip()
        for i, g in enumerate(trip.groupings):
            if g.id == gid:
                return i, g
        raise HTTPException(status_code=404, detail=f"Grouping '{gid}' not found")

    def _has_cycle(trip: Trip, grouping_id: str, proposed_parent_id: str | None) -> bool:
        if not proposed_parent_id:
            return False
        visited: set[str] = set()
        current = proposed_parent_id
        while current:
            if current == grouping_id:
                return True
            if current in visited:
                return True
            visited.add(current)
            parent = next((g for g in trip.groupings if g.id == current), None)
            current = parent.parent_id if parent else None
        return False

    @app.get("/api/groupings")
    def list_groupings():
        return _trip().groupings

    @app.post("/api/groupings", status_code=201)
    def create_grouping(request: Request, background_tasks: BackgroundTasks):
        import asyncio
        body = asyncio.get_event_loop().run_until_complete(request.json())
        trip = _trip()
        # Auto-assign color if not provided
        if not body.get("color"):
            from vacationeer.theme import next_grouping_color
            used = [g.color for g in trip.groupings]
            body["color"] = next_grouping_color(used)
        # Generate slug ID
        gid = slugify(body.get("name", "group"))
        if any(g.id == gid for g in trip.groupings):
            gid = f"{gid}-{uuid4().hex[:4]}"
        body["id"] = gid
        # Validate parent_id
        if body.get("parent_id") and not any(g.id == body["parent_id"] for g in trip.groupings):
            raise HTTPException(status_code=422, detail=f"Parent grouping '{body['parent_id']}' not found")
        grouping = Grouping(**body)
        trip.groupings.append(grouping)
        background_tasks.add_task(_rebuild_app_only, trip, trip_path, output_dir)
        log.info("Created grouping: %s (%s)", grouping.name, grouping.id)
        return grouping

    @app.patch("/api/groupings/{grouping_id}")
    def update_grouping(grouping_id: str, request: Request, background_tasks: BackgroundTasks):
        import asyncio
        body = asyncio.get_event_loop().run_until_complete(request.json())
        trip = _trip()
        idx, grouping = _find_grouping(grouping_id)
        if "parent_id" in body and _has_cycle(trip, grouping_id, body["parent_id"]):
            raise HTTPException(status_code=422, detail="Circular parent reference")
        for key, val in body.items():
            if key != "id" and hasattr(grouping, key):
                setattr(grouping, key, val)
        trip.groupings[idx] = grouping
        background_tasks.add_task(_rebuild_app_only, trip, trip_path, output_dir)
        log.info("Updated grouping: %s", grouping_id)
        return grouping

    @app.delete("/api/groupings/{grouping_id}")
    def delete_grouping(grouping_id: str, background_tasks: BackgroundTasks):
        trip = _trip()
        idx, _ = _find_grouping(grouping_id)
        trip.groupings.pop(idx)
        # Clear parent_id on orphaned children
        for g in trip.groupings:
            if g.parent_id == grouping_id:
                g.parent_id = None
        background_tasks.add_task(_rebuild_app_only, trip, trip_path, output_dir)
        log.info("Deleted grouping: %s", grouping_id)
        return {"ok": True}

    @app.post("/api/groupings/{grouping_id}/members/{attraction_id}", status_code=201)
    def add_grouping_member(grouping_id: str, attraction_id: str, background_tasks: BackgroundTasks):
        trip = _trip()
        idx, grouping = _find_grouping(grouping_id)
        if attraction_id not in [a.id for a in trip.attractions]:
            raise HTTPException(status_code=404, detail=f"Attraction '{attraction_id}' not found")
        if attraction_id not in grouping.member_ids:
            grouping.member_ids.append(attraction_id)
            trip.groupings[idx] = grouping
            background_tasks.add_task(_rebuild_app_only, trip, trip_path, output_dir)
        log.info("Added %s to grouping %s", attraction_id, grouping_id)
        return grouping

    @app.delete("/api/groupings/{grouping_id}/members/{attraction_id}")
    def remove_grouping_member(grouping_id: str, attraction_id: str, background_tasks: BackgroundTasks):
        trip = _trip()
        idx, grouping = _find_grouping(grouping_id)
        if attraction_id in grouping.member_ids:
            grouping.member_ids.remove(attraction_id)
            trip.groupings[idx] = grouping
            background_tasks.add_task(_rebuild_app_only, trip, trip_path, output_dir)
        log.info("Removed %s from grouping %s", attraction_id, grouping_id)
        return grouping

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

    @app.put("/api/days/{day_date}/activities/reorder")
    async def reorder_activities(day_date: str, request: Request, background_tasks: BackgroundTasks):
        idx, day = _find_day(day_date)
        trip = _trip()
        raw = await request.json()
        activity_ids = raw.get("activity_ids", [])

        id_order = {aid: i for i, aid in enumerate(activity_ids)}
        day.activities.sort(key=lambda a: id_order.get(a.id, 999))
        trip.days[idx] = day
        background_tasks.add_task(_rebuild_app_only, trip, trip_path, output_dir)
        return {"ok": True, "order": activity_ids}

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

    @app.post("/api/chat/add")
    async def chat_add(request: Request):
        """AI-powered attraction research: search web, return structured attraction data."""
        from vacationeer.pipeline.ai_provider import get_provider

        trip = _trip()
        raw = await request.json()
        query = raw.get("query", "").strip()
        if not query:
            raise HTTPException(status_code=422, detail="query is required")

        log.info("POST /api/chat/add query=%s", query)

        try:
            provider = get_provider()
        except RuntimeError as exc:
            raise HTTPException(status_code=503, detail=str(exc))

        categories = ", ".join(c.value for c in Category)
        prompt = (
            f'Research "{query}" in {trip.destination} and return ONLY valid JSON (no markdown, no explanation) '
            f'with this exact structure:\n'
            f'{{"name":"...","description":"2-3 sentences","category":"one of: {categories}",'
            f'"lat":0.0,"lng":0.0,"price_eur":0,"duration_minutes":60,'
            f'"tags":["..."],"tips":"practical visitor tip","url":"official website if known"}}\n\n'
            f'Requirements:\n'
            f'- Use real, accurate GPS coordinates for {trip.destination}\n'
            f'- price_eur: entrance fee in EUR (0 if free)\n'
            f'- duration_minutes: realistic visit time\n'
            f'- description: what makes it worth visiting\n'
            f'- tips: practical advice (best time, how to get there, what to skip)\n'
            f'- Return ONLY the JSON object, nothing else'
        )

        try:
            content = provider.complete(prompt)
            # Extract JSON from response (may have markdown wrapping)
            text = content.strip()
            if text.startswith("```"):
                text = re.sub(r'^```\w*\n?', '', text)
                text = re.sub(r'\n?```$', '', text)
            attraction = _json.loads(text)
            # Build a summary from the data
            summary = ""
            if attraction.get("description"):
                summary = attraction["description"]
            if attraction.get("tips"):
                summary += "\n\nTip: " + attraction["tips"]
            log.info("chat/add: parsed attraction %s", attraction.get("name"))
            return {"attraction": attraction, "summary": summary}
        except (_json.JSONDecodeError, ValueError) as e:
            log.error("chat/add: failed to parse AI response: %s\nRaw: %s", e, content[:500])
            return {"detail": f"Could not parse attraction data. AI returned: {content[:200]}"}
        except Exception as exc:
            log.error("chat/add error: %s", exc)
            raise HTTPException(status_code=500, detail=f"AI error: {exc}")

    @app.post("/api/chat")
    async def chat(request: Request):
        from vacationeer.pipeline.ai_provider import get_provider

        trip = _trip()
        raw = await request.json()
        log.info("POST /api/chat")

        try:
            body = ChatRequest(**raw)
        except Exception as exc:
            raise HTTPException(status_code=422, detail=str(exc))

        try:
            provider = get_provider()
        except RuntimeError as exc:
            raise HTTPException(status_code=503, detail=str(exc))

        system_prompt = _build_chat_system_prompt(trip)
        data_tag_re = re.compile(r'<<(GET_ATTRACTIONS|GET_SCHEDULE|GET_DAY_TRIPS|GET_UNSCHEDULED)>>')
        action_tag_re = re.compile(r'<<(SCHEDULE|UNSCHEDULE):([^>]+)>>')

        def _call_provider(messages_for_api, extra_context: str | None = None):
            if provider.name == "api":
                import anthropic
                client = anthropic.Anthropic()
                api_msgs = [{"role": m.role, "content": m.content} for m in messages_for_api]
                if extra_context:
                    api_msgs.append({"role": "user", "content": extra_context})
                resp = client.messages.create(
                    model="claude-sonnet-4-20250514",
                    max_tokens=1024,
                    system=system_prompt,
                    messages=api_msgs,
                )
                return resp.content[0].text
            else:
                prompt = _format_chat_messages(messages_for_api)
                if extra_context:
                    prompt += f"\n\nSystem data:\n{extra_context}"
                return provider.complete(prompt, system=system_prompt)

        try:
            content = _call_provider(body.messages)

            # Data tool loop: if AI requests data, resolve and re-send (max 2 rounds)
            for _ in range(2):
                match = data_tag_re.search(content.strip())
                if not match:
                    break
                tag = match.group(1)
                log.info("Chat data tool: %s", tag)
                data = _resolve_tool_call(tag, trip)
                if data:
                    content = _call_provider(body.messages, extra_context=f"[{tag}]\n{data}")
                else:
                    break

            # Action tags: execute and strip from response, track if trip changed
            action_results = []
            trip_changed = False
            for m in action_tag_re.finditer(content):
                tag_content = m.group(1) + ":" + m.group(2)
                log.info("Chat action: %s", tag_content)
                result = _execute_action_tag(tag_content, trip, trip_path, output_dir)
                if result:
                    action_results.append(result)
                    if "Scheduled" in result or "Removed" in result:
                        trip_changed = True

            # Strip action tags from the text shown to user
            clean_content = action_tag_re.sub('', content).strip()

            log.info("Chat response via %s: %s chars, %d actions", provider.name, len(clean_content), len(action_results))
            resp_data: dict = {"role": "assistant", "content": clean_content}
            if action_results:
                resp_data["action_results"] = action_results
            if trip_changed:
                resp_data["trip_changed"] = True
            return resp_data
        except Exception as exc:
            log.error("Chat error (%s): %s", provider.name, exc)
            raise HTTPException(status_code=500, detail=f"AI error: {exc}")

    # ------------------------------------------------------------------
    # Static files (mounted last so API routes take priority)
    # ------------------------------------------------------------------

    output_dir.mkdir(parents=True, exist_ok=True)
    app.mount("/", StaticFiles(directory=str(output_dir), html=True), name="static")

    return app
