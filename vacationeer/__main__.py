from __future__ import annotations

from datetime import date, time
from pathlib import Path

import click

from vacationeer.maps.generator import generate_map
from vacationeer.models.trip import Trip
from vacationeer.planning import scheduler
from vacationeer.storage.json_store import JsonTripStore, load_trip, save_trip
from vacationeer.views.app_shell import generate_app
from vacationeer.views.overview import render_overview
from vacationeer.views.timeline import render_timeline

PROJECT_ROOT = Path(__file__).resolve().parent.parent


@click.group()
def cli():
    """Vacationeer - Travel planning toolkit."""
    pass


def _build_full_app(trip: Trip, output_dir: Path) -> str:
    """Generate map + app HTML, return app filename."""
    map_filename = f"{trip.dest_slug}-map.html"
    generate_map(trip, output_dir / map_filename)
    tab_contents = {
        "overview-content": render_overview(trip),
        "timeline-content": render_timeline(trip),
    }
    app_filename = f"{trip.dest_slug}-app.html"
    generate_app(trip, map_filename, output_dir / app_filename, tab_contents=tab_contents)
    return app_filename


@cli.command()
@click.argument("trip_path", type=click.Path(exists=True, path_type=Path))
@click.option(
    "-o", "--output",
    type=click.Path(path_type=Path),
    default=None,
    help="Output HTML file path. Defaults to output/<trip_name>-map.html",
)
def map(trip_path: Path, output: Path | None):
    """Generate an interactive map from a trip JSON file."""
    trip = load_trip(trip_path)
    if output is None:
        output = PROJECT_ROOT / "output" / f"{trip.dest_slug}-map.html"
    result = generate_map(trip, output)
    click.echo(f"Map generated: {result}")


@cli.command()
@click.argument("trip_path", type=click.Path(exists=True, path_type=Path))
def info(trip_path: Path):
    """Show trip summary."""
    trip = load_trip(trip_path)
    click.echo(f"Trip: {trip.name}")
    click.echo(f"Destination: {trip.destination}")
    click.echo(f"Dates: {trip.start_date} to {trip.end_date}")
    click.echo(f"Attractions: {len(trip.attractions)}")
    click.echo(f"Days planned: {len(trip.days)}")
    for cat_name, count in _count_by_category(trip):
        click.echo(f"  {cat_name}: {count}")


@cli.command()
@click.argument("trip_path", type=click.Path(exists=True, path_type=Path))
def build(trip_path: Path):
    """Generate the full app: map + app shell with all tabs."""
    trip = load_trip(trip_path)
    output_dir = PROJECT_ROOT / "output"
    app_filename = _build_full_app(trip, output_dir)
    click.echo(f"Map generated: {trip.dest_slug}-map.html")
    click.echo(f"App generated: {output_dir / app_filename}")


@cli.command()
@click.argument("trip_path", type=click.Path(exists=True, path_type=Path))
@click.option("-p", "--port", default=8080, help="Port to serve on")
def serve(trip_path: Path, port: int):
    """Build and serve the full app via FastAPI + uvicorn.

    Requires: pip install fastapi uvicorn
    """
    import logging
    import threading
    import webbrowser

    import uvicorn

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")

    from vacationeer.server import create_app

    trip_path = trip_path.resolve()
    output_dir = PROJECT_ROOT / "output"

    # Initial build so static files exist before first request
    trip = load_trip(trip_path)
    app_filename = _build_full_app(trip, output_dir)

    app = create_app(trip_path, output_dir)

    url = f"http://localhost:{port}/{app_filename}"
    click.echo(f"Serving at {url} (Ctrl+C to stop)")
    click.echo(f"API available at http://localhost:{port}/api/trip")
    threading.Timer(1.0, lambda: webbrowser.open(url)).start()
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")


def _parse_date(value: str) -> date:
    return date.fromisoformat(value)


def _parse_time(value: str | None) -> time | None:
    if value is None:
        return None
    return time.fromisoformat(value)


# --- Planning CLI commands ---


@cli.command("init-days")
@click.argument("trip_path", type=click.Path(exists=True, path_type=Path))
def init_days(trip_path: Path):
    """Create empty days for each date in the trip range."""
    store = JsonTripStore(trip_path)
    trip = store.load()
    before = len(trip.days)
    scheduler.init_days(trip)
    store.save(trip)
    click.echo(f"Days: {before} -> {len(trip.days)}")


@cli.command()
@click.argument("trip_path", type=click.Path(exists=True, path_type=Path))
@click.argument("attraction_id")
@click.argument("target_date")
@click.option("-t", "--time", "start_time", default=None, help="Start time HH:MM")
def schedule(trip_path: Path, attraction_id: str, target_date: str, start_time: str | None):
    """Schedule an attraction onto a day."""
    store = JsonTripStore(trip_path)
    trip = store.load()
    scheduler.schedule(trip, attraction_id, _parse_date(target_date), _parse_time(start_time))
    store.save(trip)
    click.echo(f"Scheduled {attraction_id} on {target_date}")


@cli.command("schedule-day-trip")
@click.argument("trip_path", type=click.Path(exists=True, path_type=Path))
@click.argument("day_trip_id")
@click.argument("target_date")
@click.option("-d", "--depart", default=None, help="Departure time HH:MM")
def schedule_day_trip(trip_path: Path, day_trip_id: str, target_date: str, depart: str | None):
    """Schedule a day trip onto a day (expands into activities)."""
    store = JsonTripStore(trip_path)
    trip = store.load()
    scheduler.schedule_day_trip(trip, day_trip_id, _parse_date(target_date), _parse_time(depart))
    store.save(trip)
    click.echo(f"Day trip {day_trip_id} scheduled on {target_date}")


@cli.command()
@click.argument("trip_path", type=click.Path(exists=True, path_type=Path))
@click.argument("activity_id")
def unschedule(trip_path: Path, activity_id: str):
    """Remove an activity from its day."""
    store = JsonTripStore(trip_path)
    trip = store.load()
    scheduler.unschedule(trip, activity_id)
    store.save(trip)
    click.echo(f"Unscheduled {activity_id}")


@cli.command()
@click.argument("trip_path", type=click.Path(exists=True, path_type=Path))
def backlog(trip_path: Path):
    """Show unscheduled attractions and day trips."""
    trip = load_trip(trip_path)
    attractions, day_trips = scheduler.get_unscheduled(trip)

    if attractions:
        click.echo(f"\nUnscheduled attractions ({len(attractions)}):")
        for a in attractions:
            click.echo(f"  {a.id}  {a.name} [{a.category.value}]")

    if day_trips:
        click.echo(f"\nUnscheduled day trips ({len(day_trips)}):")
        for dt in day_trips:
            click.echo(f"  {dt.id}  {dt.name} -> {dt.destination}")

    if not attractions and not day_trips:
        click.echo("Everything is scheduled!")


@cli.command("swap-days")
@click.argument("trip_path", type=click.Path(exists=True, path_type=Path))
@click.argument("date1")
@click.argument("date2")
def swap_days(trip_path: Path, date1: str, date2: str):
    """Swap activities between two days."""
    store = JsonTripStore(trip_path)
    trip = store.load()
    scheduler.swap_days(trip, _parse_date(date1), _parse_date(date2))
    store.save(trip)
    click.echo(f"Swapped {date1} <-> {date2}")


@cli.command("move-activity")
@click.argument("trip_path", type=click.Path(exists=True, path_type=Path))
@click.argument("activity_id")
@click.argument("target_date")
def move_activity(trip_path: Path, activity_id: str, target_date: str):
    """Move an activity to a different day."""
    store = JsonTripStore(trip_path)
    trip = store.load()
    scheduler.move_activity(trip, activity_id, _parse_date(target_date))
    store.save(trip)
    click.echo(f"Moved {activity_id} to {target_date}")


def _count_by_category(trip):
    from collections import Counter
    counts = Counter(a.category.value for a in trip.attractions)
    return sorted(counts.items())


# --- Trip management ---

ACTIVE_TRIP_FILE = PROJECT_ROOT / ".active-trip"


def _get_active_trip() -> str | None:
    """Read the active trip slug from .active-trip file."""
    if ACTIVE_TRIP_FILE.exists():
        return ACTIVE_TRIP_FILE.read_text(encoding="utf-8").strip()
    return None


def _resolve_active_path(
    given: Path | None,
    subdirectory: str,
    filename: str,
) -> Path:
    """Resolve a path from explicit arg or active trip fallback.

    Args:
        given: Explicit path from CLI argument (None if not provided).
        subdirectory: Folder under PROJECT_ROOT (e.g. "trips").
        filename: File to look for (e.g. "trip.json", "trip-config.json").
    """
    if given:
        return given
    slug = _get_active_trip()
    if slug:
        candidate = PROJECT_ROOT / subdirectory / slug / filename
        if candidate.exists():
            return candidate
    raise click.UsageError(
        f"No path given and no active trip set. "
        f"Use 'vacationeer use <slug>' or pass a path."
    )


def _resolve_trip_path(trip_path: Path | None) -> Path:
    return _resolve_active_path(trip_path, "trips", "trip.json")


def _resolve_config_path(config_path: Path | None) -> Path:
    return _resolve_active_path(config_path, "trips", "trip-config.json")


@cli.command("trips")
def list_trips():
    """List all trips and show which is active."""
    import json as _json

    trips_dir = PROJECT_ROOT / "trips"
    active = _get_active_trip()

    if not trips_dir.exists():
        click.echo("No trips found.")
        return

    for trip_dir in sorted(trips_dir.iterdir()):
        if not trip_dir.is_dir():
            continue
        slug = trip_dir.name
        marker = " *" if slug == active else "  "

        # Try to read trip name from trip.json or trip-config.json
        name = slug
        trip_json = trip_dir / "trip.json"
        config_json = trip_dir / "trip-config.json"
        has_trip = trip_json.exists()
        has_config = config_json.exists()

        if has_trip:
            try:
                data = _json.loads(trip_json.read_text(encoding="utf-8"))
                name = data.get("name", slug)
            except Exception:
                pass
        elif has_config:
            try:
                data = _json.loads(config_json.read_text(encoding="utf-8"))
                name = data.get("name", slug)
            except Exception:
                pass

        # Status indicators
        status = []
        if has_config:
            status.append("config")
        data_dir = PROJECT_ROOT / "data" / slug
        if (data_dir / "attractions-and-activities.md").exists():
            status.append("research")
        if has_trip:
            status.append("ready")
        status_str = " [" + ", ".join(status) + "]" if status else ""

        click.echo(f"{marker} {slug:25s} {name}{status_str}")

    if not active:
        click.echo("\nNo active trip. Set one with: python -m vacationeer use <slug>")


@cli.command("use")
@click.argument("slug")
def use_trip(slug: str):
    """Set the active trip by slug (e.g. 'valencia-2026')."""
    trip_dir = PROJECT_ROOT / "trips" / slug
    if not trip_dir.exists():
        raise click.UsageError(f"Trip '{slug}' not found in trips/")
    ACTIVE_TRIP_FILE.write_text(slug, encoding="utf-8")
    click.echo(f"Active trip: {slug}")


# --- Pipeline CLI commands ---

PROVIDER_OPTION = click.option(
    "--provider",
    type=click.Choice(["claude-code", "api", "manual"], case_sensitive=False),
    default=None,
    help="AI provider override. Default: auto-detect (claude-code > api > manual).",
)


@cli.command("new-trip")
def new_trip():
    """Interactive questionnaire to set up a new trip."""
    from vacationeer.pipeline.questionnaire import run_questionnaire, save_config

    config = run_questionnaire(PROJECT_ROOT)
    config_path, data_dir = save_config(config, PROJECT_ROOT)

    # Auto-set as active trip
    ACTIVE_TRIP_FILE.write_text(config["id"], encoding="utf-8")

    click.echo(f"\nTrip workspace created!")
    click.echo(f"  Config: {config_path}")
    click.echo(f"  Data:   {data_dir}")
    click.echo(f"  Active: {config['id']}")
    click.echo(f"\nNext step:")
    click.echo(f"  python -m vacationeer gen-research")


@cli.command("gen-research")
@click.argument("config_path", type=click.Path(exists=True, path_type=Path), required=False, default=None)
@click.option("--light", is_flag=True, default=True, help="Light mode: fewer attractions, faster output. Use --no-light for full research.")
@PROVIDER_OPTION
def gen_research(config_path: Path | None, light: bool, provider: str | None):
    """Generate destination research (3 MD files) using AI.

    CONFIG_PATH defaults to the active trip's trip-config.json if not given.
    """
    import json as _json

    from vacationeer.pipeline.ai_provider import get_provider
    from vacationeer.pipeline.research import generate_research

    config_path = _resolve_config_path(config_path)
    config = _json.loads(config_path.read_text(encoding="utf-8"))
    slug = config["id"]
    data_dir = PROJECT_ROOT / "data" / slug

    ai = get_provider(provider)
    mode = "light" if light else "full"
    click.echo(f"Using AI provider: {ai.name} ({mode} research)")

    saved = generate_research(config, data_dir, ai, light=light)

    if len(saved) > 1:
        click.echo(f"\nResearch complete! Review the files in {data_dir}")
        click.echo(f"Then run:")
        click.echo(f"  python -m vacationeer import-trip {config_path}")


@cli.command("import-trip")
@click.argument("config_path", type=click.Path(exists=True, path_type=Path), required=False, default=None)
@click.option(
    "--json-input",
    type=click.Path(exists=True, path_type=Path),
    default=None,
    help="Path to a pre-generated JSON file to validate and save.",
)
@PROVIDER_OPTION
def import_trip(config_path: Path | None, json_input: Path | None, provider: str | None):
    """Convert research MD files to trip.json.

    CONFIG_PATH defaults to the active trip's trip-config.json if not given.
    """
    import json as _json

    from vacationeer.pipeline.converter import convert_to_trip, validate_and_save

    config_path = _resolve_config_path(config_path)
    config = _json.loads(config_path.read_text(encoding="utf-8"))
    slug = config["id"]
    data_dir = PROJECT_ROOT / "data" / slug
    output_path = PROJECT_ROOT / "trips" / slug / "trip.json"

    if json_input:
        # Direct JSON validation mode
        json_text = json_input.read_text(encoding="utf-8")
        try:
            trip = validate_and_save(json_text, output_path)
            click.echo(f"Trip saved: {output_path}")
            click.echo(f"  Attractions: {len(trip.attractions)}")
            click.echo(f"  Day trips: {len(trip.day_trips)}")
            click.echo(f"\nNext: python -m vacationeer serve {output_path}")
        except Exception as e:
            click.echo(f"Validation failed: {e}", err=True)
        return

    from vacationeer.pipeline.ai_provider import get_provider

    ai = get_provider(provider)
    click.echo(f"Using AI provider: {ai.name}")

    convert_to_trip(config, data_dir, output_path, ai)


# --- Sync CLI commands ---


def _resolve_data_dir(trip_path: Path) -> Path:
    """Infer data directory from trip path: trips/<slug>/trip.json -> data/<slug>/."""
    slug = trip_path.resolve().parent.name
    data_dir = PROJECT_ROOT / "data" / slug
    if not data_dir.exists():
        raise click.UsageError(f"Data directory not found: {data_dir}")
    return data_dir


def _read_md_files(data_dir: Path) -> dict[str, str]:
    """Read all markdown files from data directory."""
    md_files = {}
    for md_path in sorted(data_dir.glob("*.md")):
        md_files[md_path.name] = md_path.read_text(encoding="utf-8")
    return md_files


def _attraction_to_marker(a) -> dict[str, str]:
    """Convert an Attraction to marker data dict."""
    from vacationeer.sync.markers import format_location
    data: dict[str, str] = {"id": a.id, "type": "attraction"}
    if a.name:
        data["name"] = a.name
    if a.description:
        data["description"] = a.description
    if a.price_eur is not None:
        data["price_eur"] = str(a.price_eur)
    if a.duration_minutes is not None:
        data["duration_minutes"] = str(a.duration_minutes)
    data["location"] = format_location(a.location.lat, a.location.lng, a.location.address)
    if a.expected_score is not None:
        data["expected_score"] = str(a.expected_score)
    if a.tips:
        data["tips"] = a.tips
    data["url"] = str(a.url) if a.url else "null"
    return data


def _day_trip_to_marker(dt) -> dict[str, str]:
    """Convert a DayTrip to marker data dict."""
    from vacationeer.sync.markers import format_location
    data: dict[str, str] = {"id": dt.id, "type": "day_trip"}
    data["name"] = dt.name
    data["destination"] = dt.destination
    if dt.description:
        data["description"] = dt.description
    data["location"] = format_location(dt.location.lat, dt.location.lng, dt.location.address)
    if dt.total_price_eur is not None:
        data["total_price_eur"] = str(dt.total_price_eur)
    if dt.total_duration_minutes is not None:
        data["total_duration_minutes"] = str(dt.total_duration_minutes)
    if dt.expected_score is not None:
        data["expected_score"] = str(dt.expected_score)
    if dt.tips:
        data["tips"] = dt.tips
    return data


@cli.command("inject-markers")
@click.argument("trip_path", type=click.Path(exists=True, path_type=Path))
def inject_markers(trip_path: Path):
    """One-time: inject @vacationeer marker blocks into existing MD files."""
    from vacationeer.sync.md_writer import inject_all_markers

    trip = load_trip(trip_path)
    data_dir = _resolve_data_dir(trip_path)
    md_files = _read_md_files(data_dir)

    # Build marker data for all attractions
    items = [_attraction_to_marker(a) for a in trip.attractions]

    # Build marker data for day trips and their sub-attractions
    for dt in trip.day_trips:
        items.append(_day_trip_to_marker(dt))
        for sub in dt.sub_attractions:
            items.append(_attraction_to_marker(sub))

    # Inject into each MD file (items only match where headings are found)
    total_injected = 0
    all_injected_ids: set[str] = set()

    for filename, md_text in md_files.items():
        updated, injected_ids = inject_all_markers(md_text, items)

        if injected_ids:
            (data_dir / filename).write_text(updated, encoding="utf-8")
            click.echo(f"  {filename}: +{len(injected_ids)} markers")
            total_injected += len(injected_ids)
            all_injected_ids.update(injected_ids)
        else:
            click.echo(f"  {filename}: no new markers")

    # Report unmatched items
    all_item_ids = {item.get("id", "") for item in items}
    unmatched = all_item_ids - all_injected_ids
    # Exclude items that already had markers
    from vacationeer.sync.markers import find_all_markers as _find
    existing_ids: set[str] = set()
    for md_text in _read_md_files(data_dir).values():
        existing_ids.update(m.data.get("id", "") for m in _find(md_text))
    unmatched -= existing_ids

    click.echo(f"\nInjected {total_injected} marker blocks total.")
    if unmatched:
        click.echo(f"Could not match {len(unmatched)} item(s) to any MD heading:")
        for uid in sorted(unmatched):
            click.echo(f"  {uid}")


@cli.command("sync-status")
@click.argument("trip_path", type=click.Path(exists=True, path_type=Path))
def sync_status(trip_path: Path):
    """Show what differs between MD markers and JSON (dry run)."""
    from vacationeer.sync.md_parser import extract_all_from_files
    from vacationeer.sync.sync_engine import compare

    trip = load_trip(trip_path)
    data_dir = _resolve_data_dir(trip_path)
    md_files = _read_md_files(data_dir)
    md_items = extract_all_from_files(md_files)

    if not md_items:
        click.echo("No @vacationeer markers found in MD files. Run inject-markers first.")
        return

    result = compare(md_items, trip)

    if not result.updates and not result.new_in_md and not result.new_in_json:
        click.echo("MD and JSON are in sync.")
        return

    if result.updates:
        click.echo(f"\nField differences ({len(result.updates)}):")
        for u in result.updates:
            click.echo(f"  {u.item_id}.{u.field}: MD={u.md_value!r} vs JSON={u.json_value!r}")

    if result.new_in_md:
        click.echo(f"\nIn MD only ({len(result.new_in_md)}):")
        for item_id in result.new_in_md:
            click.echo(f"  {item_id}")

    if result.new_in_json:
        click.echo(f"\nIn JSON only ({len(result.new_in_json)}):")
        for item_id in result.new_in_json:
            click.echo(f"  {item_id}")


@cli.command("sync-to-md")
@click.argument("trip_path", type=click.Path(exists=True, path_type=Path))
def sync_to_md(trip_path: Path):
    """JSON -> MD: update marker blocks in MD files from JSON values."""
    from vacationeer.sync.md_parser import extract_all_from_files
    from vacationeer.sync.md_writer import update_markers
    from vacationeer.sync.sync_engine import build_md_updates, compare

    trip = load_trip(trip_path)
    data_dir = _resolve_data_dir(trip_path)
    md_files = _read_md_files(data_dir)
    md_items = extract_all_from_files(md_files)

    if not md_items:
        click.echo("No @vacationeer markers found in MD files. Run inject-markers first.")
        return

    result = compare(md_items, trip)
    if not result.updates:
        click.echo("MD and JSON are in sync. Nothing to update.")
        return

    md_updates = build_md_updates(result)

    for filename, md_text in md_files.items():
        updated = update_markers(md_text, md_updates)
        if updated != md_text:
            (data_dir / filename).write_text(updated, encoding="utf-8")
            click.echo(f"  Updated: {filename}")

    click.echo(f"\nSynced {len(result.updates)} field(s) from JSON to MD.")


@cli.command("sync-from-md")
@click.argument("trip_path", type=click.Path(exists=True, path_type=Path))
def sync_from_md(trip_path: Path):
    """MD -> JSON: update JSON from marker blocks in MD files."""
    from vacationeer.sync.md_parser import extract_all_from_files
    from vacationeer.sync.sync_engine import apply_to_trip, compare

    store = JsonTripStore(trip_path)
    trip = store.load()
    data_dir = _resolve_data_dir(trip_path)
    md_files = _read_md_files(data_dir)
    md_items = extract_all_from_files(md_files)

    if not md_items:
        click.echo("No @vacationeer markers found in MD files. Run inject-markers first.")
        return

    result = compare(md_items, trip)
    if not result.updates and not result.new_in_md:
        click.echo("MD and JSON are in sync. Nothing to update.")
        return

    if result.updates:
        apply_to_trip(result, trip)
        click.echo(f"Updated {len(result.updates)} field(s) from MD to JSON.")

    if result.new_in_md:
        click.echo(f"Note: {len(result.new_in_md)} item(s) in MD have no JSON match: {', '.join(result.new_in_md)}")

    store.save(trip)
    click.echo("JSON saved.")


if __name__ == "__main__":
    cli()
