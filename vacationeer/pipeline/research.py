from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path

import click

from vacationeer.pipeline.ai_provider import AIProvider, ManualFallback, ManualProvider
from vacationeer.pipeline.templates import (
    DAY_TRIPS_SECTION,
    LIGHT_RESEARCH_PREFIX,
    NO_DAY_TRIPS_SECTION,
    RESEARCH_PROMPT,
    RESEARCH_SYSTEM,
)


def _build_date_description(config: dict) -> str:
    if config.get("dates_approximate"):
        return f"{config['start_date']} to {config['end_date']} (approximate)"
    try:
        d1 = date.fromisoformat(config["start_date"])
        d2 = date.fromisoformat(config["end_date"])
        num_days = (d2 - d1).days
        return f"{config['start_date']} to {config['end_date']} ({num_days} days)"
    except ValueError:
        return f"{config['start_date']} to {config['end_date']}"


def _build_budget_description(config: dict) -> str:
    parts = []
    if config.get("budget_eur"):
        parts.append(f"{config['budget_eur']} EUR total")
    prefs = config.get("preferences", {})
    if prefs.get("budget_per_day_eur"):
        parts.append(f"{prefs['budget_per_day_eur']} EUR/day/person")
    return " | ".join(parts) if parts else "No specific budget"


def _build_optional_sections(config: dict) -> str:
    lines = []
    if config.get("context"):
        lines.append(f"- **Context:** {config['context']}")
    if config.get("must_do"):
        lines.append(f"- **Must-do:** {config['must_do']}")
    if config.get("accommodation_area"):
        lines.append(f"- **Accommodation area:** {config['accommodation_area']}")
    if config.get("arrival_method"):
        lines.append(f"- **Arriving by:** {config['arrival_method']}")
    prefs = config.get("preferences", {})
    if prefs.get("avoid"):
        lines.append(f"- **Avoid:** {', '.join(prefs['avoid'])}")
    return "\n".join(lines)


def build_research_prompt(config: dict, *, light: bool = False) -> str:
    """Build the full research prompt from a trip config."""
    prefs = config.get("preferences", {})
    interests = ", ".join(prefs.get("interests", []))

    day_trips_section = (
        DAY_TRIPS_SECTION.format(travelers=config.get("travelers", 2))
        if config.get("include_day_trips", True)
        else NO_DAY_TRIPS_SECTION
    )

    prompt = RESEARCH_PROMPT.format(
        destination=config["destination"],
        date_description=_build_date_description(config),
        travelers=config.get("travelers", 2),
        budget_description=_build_budget_description(config),
        interests=interests or "general sightseeing",
        pace=prefs.get("pace", "moderate"),
        optional_sections=_build_optional_sections(config),
        day_trips_section=day_trips_section,
        current_year=date.today().year,
    )

    if light:
        prompt = LIGHT_RESEARCH_PREFIX + prompt

    return prompt


def _parse_files_from_response(response: str) -> dict[str, str]:
    """Parse the 3 MD files from the AI response using the file markers."""
    files = {}
    pattern = r"===FILE:\s*(.+?)===\s*\n(.*?)(?====FILE:|$)"
    matches = re.findall(pattern, response, re.DOTALL)

    for filename, content in matches:
        filename = filename.strip()
        content = content.strip()
        files[filename] = content

    # Fallback: if markers not found, treat entire response as attractions file
    if not files:
        files["attractions-and-activities.md"] = response.strip()

    return files


def generate_research(
    config: dict,
    data_dir: Path,
    provider: AIProvider,
    *,
    light: bool = False,
) -> dict[str, Path]:
    """Generate research MD files using the AI provider.

    Returns a dict mapping filename -> saved path.
    """
    prompt = build_research_prompt(config, light=light)

    # Always save the prompt for reference
    instructions_path = data_dir / "research-instructions.md"
    data_dir.mkdir(parents=True, exist_ok=True)
    instructions_path.write_text(prompt, encoding="utf-8")
    click.echo(f"Research instructions saved: {instructions_path}")

    # If manual provider, set its output path
    if isinstance(provider, ManualProvider):
        provider._output_path = instructions_path

    try:
        response = provider.complete(prompt, system=RESEARCH_SYSTEM)
    except ManualFallback as e:
        click.echo(f"\nManual mode: Paste the contents of {e.path} into Claude.")
        click.echo("Save the 3 output files to:")
        click.echo(f"  {data_dir / 'attractions-and-activities.md'}")
        click.echo(f"  {data_dir / 'day-trips.md'}")
        click.echo(f"  {data_dir / 'good-to-know.md'}")
        return {"research-instructions.md": instructions_path}

    # Parse and save the files
    parsed_files = _parse_files_from_response(response)
    saved = {"research-instructions.md": instructions_path}

    expected = [
        "attractions-and-activities.md",
        "day-trips.md",
        "good-to-know.md",
    ]
    for filename in expected:
        content = parsed_files.get(filename, "")
        if content:
            path = data_dir / filename
            path.write_text(content, encoding="utf-8")
            saved[filename] = path
            click.echo(f"Saved: {path}")
        else:
            click.echo(f"Warning: {filename} was not found in AI response")

    # Save raw response for debugging
    raw_path = data_dir / "research-raw-response.md"
    raw_path.write_text(response, encoding="utf-8")

    return saved
