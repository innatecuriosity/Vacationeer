from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path

import click


INTEREST_OPTIONS = [
    "history", "nature", "food", "science", "art", "architecture",
    "nightlife", "shopping", "sports", "beach", "wine", "photography",
]

PACE_OPTIONS = ["relaxed", "moderate", "fast"]
ARRIVAL_OPTIONS = ["flight", "train", "car", "bus"]


def _slugify(destination: str, year: str) -> str:
    """Generate a slug like 'rome-2026' from destination and year."""
    slug = re.sub(r"[^a-z0-9]+", "-", destination.lower()).strip("-")
    # Extract just city name (before comma if present)
    slug = slug.split("-")[0] if "-" in slug else slug
    return f"{slug}-{year}"


def _get_season(month: int) -> str:
    if month in (3, 4, 5):
        return "Spring"
    elif month in (6, 7, 8):
        return "Summer"
    elif month in (9, 10, 11):
        return "Autumn"
    return "Winter"


def _parse_year(date_str: str) -> str:
    """Extract year from a date string (exact or approximate)."""
    match = re.search(r"20\d{2}", date_str)
    return match.group() if match else str(date.today().year)


def _unique_slug(base_slug: str, project_root: Path) -> str:
    """Ensure slug doesn't collide with existing trips."""
    trips_dir = project_root / "trips"
    if not (trips_dir / base_slug).exists():
        return base_slug
    for i in range(2, 100):
        candidate = f"{base_slug}-{i}"
        if not (trips_dir / candidate).exists():
            return candidate
    return base_slug


def run_questionnaire(project_root: Path) -> dict:
    """Run the interactive questionnaire and return the config dict."""
    click.echo("\n=== New Trip Setup ===\n")

    # Required fields
    destination = click.prompt("Destination (e.g. 'Rome, Italy')")

    # Dates
    has_exact = click.confirm("Do you have exact travel dates?", default=True)
    if has_exact:
        start_date = click.prompt("Start date (YYYY-MM-DD)")
        end_date = click.prompt("End date (YYYY-MM-DD)")
        dates_approximate = False
        year = _parse_year(start_date)
        try:
            parsed = date.fromisoformat(start_date)
            season = _get_season(parsed.month)
        except ValueError:
            season = ""
    else:
        start_date = click.prompt("Approximate dates (e.g. 'mid-May 2026', 'early June 2026')")
        end_date = click.prompt("Approximate duration or end (e.g. '~7 days', 'late May 2026')")
        dates_approximate = True
        year = _parse_year(start_date)
        season = ""

    # Trip name
    default_name = f"{destination.split(',')[0].strip()} {season} {year}".strip()
    name = click.prompt("Trip name", default=default_name)

    travelers = click.prompt("Number of travelers", default=2, type=int)

    # Interests
    click.echo(f"\nAvailable interests: {', '.join(INTEREST_OPTIONS)}")
    interests_input = click.prompt(
        "Your interests (comma-separated, add custom ones too)",
        default="history, food",
    )
    interests = [i.strip() for i in interests_input.split(",") if i.strip()]

    # Pace
    pace = click.prompt(
        "Travel pace",
        type=click.Choice(PACE_OPTIONS, case_sensitive=False),
        default="moderate",
    )

    # Optional fields
    click.echo("\n--- Optional (press Enter to skip) ---\n")

    budget_input = click.prompt("Total budget in EUR", default="", show_default=False)
    budget_eur = float(budget_input) if budget_input else None

    if budget_eur and not dates_approximate:
        try:
            d1 = date.fromisoformat(start_date)
            d2 = date.fromisoformat(end_date)
            num_days = max((d2 - d1).days, 1)
            auto_daily = round(budget_eur / num_days / travelers, 2)
            budget_per_day = click.prompt(
                "Budget per person per day (EUR)",
                default=auto_daily,
                type=float,
            )
        except ValueError:
            budget_per_day = None
    else:
        daily_input = click.prompt("Budget per person per day (EUR)", default="", show_default=False)
        budget_per_day = float(daily_input) if daily_input else None

    avoid_input = click.prompt(
        "Things to avoid (comma-separated)",
        default="",
        show_default=False,
    )
    avoid = [a.strip() for a in avoid_input.split(",") if a.strip()]

    must_do = click.prompt(
        "Must-do places or experiences",
        default="",
        show_default=False,
    )

    context = click.prompt(
        "Travel context (e.g. 'anniversary trip', 'with toddler')",
        default="",
        show_default=False,
    )

    accommodation = click.prompt(
        "Accommodation area/neighborhood",
        default="",
        show_default=False,
    )

    arrival = click.prompt(
        "Arrival method",
        type=click.Choice([""] + ARRIVAL_OPTIONS, case_sensitive=False),
        default="",
        show_default=False,
    )

    want_day_trips = click.confirm("Include day trip research?", default=True)

    # Build config
    slug = _unique_slug(_slugify(destination, year), project_root)

    config = {
        "id": slug,
        "name": name,
        "destination": destination,
        "start_date": start_date,
        "end_date": end_date,
        "dates_approximate": dates_approximate,
        "travelers": travelers,
        "budget_eur": budget_eur,
        "preferences": {
            "interests": interests,
            "avoid": avoid,
            "pace": pace,
            "budget_per_day_eur": budget_per_day,
        },
        "context": context or None,
        "must_do": must_do or None,
        "accommodation_area": accommodation or None,
        "arrival_method": arrival or None,
        "include_day_trips": want_day_trips,
    }

    return config


def save_config(config: dict, project_root: Path) -> tuple[Path, Path]:
    """Save config and create workspace directories. Returns (config_path, data_dir)."""
    slug = config["id"]
    trips_dir = project_root / "trips" / slug
    data_dir = project_root / "data" / slug

    trips_dir.mkdir(parents=True, exist_ok=True)
    data_dir.mkdir(parents=True, exist_ok=True)

    config_path = trips_dir / "trip-config.json"
    config_path.write_text(json.dumps(config, indent=2, ensure_ascii=False), encoding="utf-8")

    return config_path, data_dir
