from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path

import click

from vacationeer.models.trip import Trip
from vacationeer.pipeline.ai_provider import AIProvider, ManualFallback, ManualProvider
from vacationeer.pipeline.templates import CONVERSION_PROMPT, CONVERSION_SYSTEM


def _read_md_file(path: Path) -> str:
    if path.exists():
        return path.read_text(encoding="utf-8")
    return ""


def _date_instruction(config: dict) -> str:
    if config.get("dates_approximate"):
        return (
            "Dates are approximate. Suggest reasonable exact dates based on "
            f"'{config['start_date']}' to '{config['end_date']}' and output "
            "them as YYYY-MM-DD in the JSON."
        )
    return "Use the exact dates from the config."


def build_conversion_prompt(config: dict, data_dir: Path) -> str:
    """Build the conversion prompt from config + MD files."""
    # Build a clean config for the prompt (without pipeline-only fields)
    trip_config = {
        "id": config["id"],
        "name": config["name"],
        "destination": config["destination"],
        "start_date": config["start_date"],
        "end_date": config["end_date"],
        "travelers": config.get("travelers", 2),
        "budget_eur": config.get("budget_eur"),
        "preferences": config.get("preferences", {}),
    }

    schema = Trip.model_json_schema()

    return CONVERSION_PROMPT.format(
        config_json=json.dumps(trip_config, indent=2),
        schema_json=json.dumps(schema, indent=2),
        date_instruction=_date_instruction(config),
        attractions_md=_read_md_file(data_dir / "attractions-and-activities.md"),
        day_trips_md=_read_md_file(data_dir / "day-trips.md"),
        good_to_know_md=_read_md_file(data_dir / "good-to-know.md"),
    )


def _extract_json(text: str) -> str:
    """Extract JSON from AI response, handling markdown fences."""
    # Try to find JSON in code fences
    match = re.search(r"```(?:json)?\s*\n(.*?)\n```", text, re.DOTALL)
    if match:
        return match.group(1).strip()
    # Try to find a top-level JSON object
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        return match.group(0).strip()
    return text.strip()


def validate_and_save(json_text: str, output_path: Path) -> Trip:
    """Validate JSON against the Trip model and save."""
    data = json.loads(json_text)
    trip = Trip.model_validate(data)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(trip.model_dump_json(indent=2), encoding="utf-8")
    return trip


def convert_to_trip(
    config: dict,
    data_dir: Path,
    output_path: Path,
    provider: AIProvider,
) -> Path | None:
    """Convert MD research files to trip.json using AI provider.

    Returns the path to trip.json if successful, None if manual fallback.
    """
    prompt = build_conversion_prompt(config, data_dir)

    # Always save the conversion prompt for reference
    prompt_path = data_dir / "conversion-prompt.md"
    prompt_path.write_text(prompt, encoding="utf-8")
    click.echo(f"Conversion prompt saved: {prompt_path}")

    # If manual provider, set its output path
    if isinstance(provider, ManualProvider):
        provider._output_path = prompt_path

    try:
        response = provider.complete(prompt, system=CONVERSION_SYSTEM)
    except ManualFallback as e:
        click.echo(f"\nManual mode: Paste the contents of {e.path} into Claude.")
        click.echo("Then run:")
        click.echo(f"  python -m vacationeer import-trip <config-path> --json-input <response.json>")
        return None

    # Extract and validate JSON
    json_text = _extract_json(response)

    # Save raw response for debugging
    raw_path = data_dir / "conversion-raw-response.json"
    raw_path.write_text(json_text, encoding="utf-8")

    try:
        trip = validate_and_save(json_text, output_path)
        click.echo(f"\nTrip saved: {output_path}")
        click.echo(f"  Attractions: {len(trip.attractions)}")
        click.echo(f"  Day trips: {len(trip.day_trips)}")
        click.echo(f"\nNext: python -m vacationeer serve {output_path}")
        return output_path
    except Exception as e:
        click.echo(f"\nValidation failed: {e}", err=True)
        click.echo(f"Raw JSON saved to: {raw_path}", err=True)
        click.echo("Fix the JSON and run:", err=True)
        config_path = output_path.parent / "trip-config.json"
        click.echo(f"  python -m vacationeer import-trip {config_path} --json-input {raw_path}", err=True)
        return None
