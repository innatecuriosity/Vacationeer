from __future__ import annotations

from datetime import date, time
from pathlib import Path

import click

from vacationeer.maps.generator import generate_map
from vacationeer.planning import scheduler
from vacationeer.storage.json_store import JsonTripStore, load_trip, save_trip
from vacationeer.views.app_shell import generate_app
from vacationeer.views.overview import render_overview
from vacationeer.views.timeline import render_timeline
from vacationeer.views.chat import render_chat

PROJECT_ROOT = Path(__file__).resolve().parent.parent


@click.group()
def cli():
    """Vacationeer - Travel planning toolkit."""
    pass


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
        output = PROJECT_ROOT / "output" / f"{trip.destination.lower().replace(' ', '-')}-map.html"
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
    dest_slug = trip.destination.lower().replace(" ", "-")

    # 1. Generate map HTML
    map_filename = f"{dest_slug}-map.html"
    generate_map(trip, output_dir / map_filename)
    click.echo(f"Map generated: {map_filename}")

    # 2. Render tab contents
    tab_contents = {
        "overview-content": render_overview(trip),
        "timeline-content": render_timeline(trip),
        "chat-content": render_chat(trip),
    }

    # 3. Generate app shell
    app_file = output_dir / f"{dest_slug}-app.html"
    generate_app(trip, map_filename, app_file, tab_contents=tab_contents)
    click.echo(f"App generated: {app_file}")


@cli.command()
@click.argument("trip_path", type=click.Path(exists=True, path_type=Path))
@click.option("-p", "--port", default=8080, help="Port to serve on")
def serve(trip_path: Path, port: int):
    """Build and serve the full app via FastAPI + uvicorn.

    Requires: pip install fastapi uvicorn
    """
    import threading
    import webbrowser

    import uvicorn

    from vacationeer.server import create_app

    trip_path = trip_path.resolve()
    output_dir = PROJECT_ROOT / "output"

    # Initial build so static files exist before first request
    trip = load_trip(trip_path)
    dest_slug = trip.destination.lower().replace(" ", "-")
    map_filename = f"{dest_slug}-map.html"
    generate_map(trip, output_dir / map_filename)
    tab_contents = {
        "overview-content": render_overview(trip),
        "timeline-content": render_timeline(trip),
        "chat-content": render_chat(trip),
    }
    app_filename = f"{dest_slug}-app.html"
    generate_app(trip, map_filename, output_dir / app_filename, tab_contents=tab_contents)

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


if __name__ == "__main__":
    cli()
