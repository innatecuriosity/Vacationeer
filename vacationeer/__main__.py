from __future__ import annotations

from pathlib import Path

import click

from vacationeer.maps.generator import generate_map
from vacationeer.storage.json_store import load_trip, save_trip

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


def _count_by_category(trip):
    from collections import Counter
    counts = Counter(a.category.value for a in trip.attractions)
    return sorted(counts.items())


if __name__ == "__main__":
    cli()
