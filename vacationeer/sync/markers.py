"""Parse and write @vacationeer HTML comment blocks in markdown files."""
from __future__ import annotations

import re
from dataclasses import dataclass


MARKER_PATTERN = re.compile(
    r"<!--\s*@vacationeer\s*\n(.*?)\n\s*-->",
    re.DOTALL,
)

# Syncable fields and their types for parsing
SYNCABLE_FIELDS = {
    "id": str,
    "type": str,  # "attraction" or "day_trip"
    "name": str,
    "description": str,
    "price_eur": float,
    "duration_minutes": int,
    "location": str,  # "lat, lng | address"
    "expected_score": float,
    "tips": str,
    "url": str,
    # Day trip extras
    "destination": str,
    "total_price_eur": float,
    "total_duration_minutes": int,
}


@dataclass
class MarkerMatch:
    """A parsed @vacationeer block with its position in the source text."""

    data: dict[str, str]
    start: int
    end: int


def parse_marker(text: str) -> dict[str, str]:
    """Extract key-value pairs from the inner content of a marker block."""
    result = {}
    for line in text.strip().splitlines():
        line = line.strip()
        if not line or ":" not in line:
            continue
        key, _, value = line.partition(": ")
        key = key.strip()
        value = value.strip()
        result[key] = value
    return result


def render_marker(data: dict[str, str | float | int | None]) -> str:
    """Produce a <!-- @vacationeer ... --> HTML comment string."""
    lines = []
    for key, value in data.items():
        if value is None:
            lines.append(f"{key}: null")
        else:
            lines.append(f"{key}: {value}")
    inner = "\n".join(lines)
    return f"<!-- @vacationeer\n{inner}\n-->"


def find_all_markers(md_text: str) -> list[MarkerMatch]:
    """Find all @vacationeer blocks in markdown text."""
    results = []
    for match in MARKER_PATTERN.finditer(md_text):
        data = parse_marker(match.group(1))
        results.append(MarkerMatch(
            data=data,
            start=match.start(),
            end=match.end(),
        ))
    return results


def coerce_value(key: str, raw: str) -> str | float | int | None:
    """Convert a raw string value to the appropriate type for a syncable field."""
    if raw == "null" or raw == "None" or raw == "":
        return None
    expected_type = SYNCABLE_FIELDS.get(key, str)
    if expected_type is float:
        return float(raw)
    if expected_type is int:
        return int(float(raw))  # handle "75.0" -> 75
    return raw


def parse_location(location_str: str) -> tuple[float, float, str | None]:
    """Parse 'lat, lng | address' into (lat, lng, address)."""
    if "|" in location_str:
        coords_part, _, address = location_str.partition("|")
        address = address.strip() or None
    else:
        coords_part = location_str
        address = None
    parts = coords_part.split(",")
    lat = float(parts[0].strip())
    lng = float(parts[1].strip())
    return lat, lng, address


def format_location(lat: float, lng: float, address: str | None) -> str:
    """Format location as 'lat, lng | address'."""
    if address:
        return f"{lat}, {lng} | {address}"
    return f"{lat}, {lng}"
