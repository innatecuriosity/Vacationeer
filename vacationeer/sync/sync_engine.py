"""Compare MD marker data vs Trip model and produce sync results."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from vacationeer.models.trip import Attraction, DayTrip, Location, Trip
from vacationeer.sync.markers import (
    coerce_value,
    format_location,
    parse_location,
)

# Fields synced between MD markers and JSON (Attraction)
ATTRACTION_SYNC_FIELDS = [
    "name", "description", "price_eur", "duration_minutes",
    "expected_score", "tips", "url",
]

# Fields synced for DayTrip
DAY_TRIP_SYNC_FIELDS = [
    "name", "description", "destination",
    "total_price_eur", "total_duration_minutes",
    "expected_score", "tips",
]


@dataclass
class FieldUpdate:
    """A single field that differs between MD and JSON."""

    item_id: str
    field: str
    md_value: Any
    json_value: Any


@dataclass
class SyncResult:
    """Result of comparing MD markers against JSON data."""

    updates: list[FieldUpdate] = field(default_factory=list)
    new_in_md: list[str] = field(default_factory=list)
    new_in_json: list[str] = field(default_factory=list)


def _get_json_value(obj: Attraction | DayTrip, field_name: str) -> Any:
    """Get a field value from a model object, handling location specially."""
    if field_name == "location":
        loc = obj.location
        return format_location(loc.lat, loc.lng, loc.address)
    val = getattr(obj, field_name, None)
    return val


def _marker_to_syncable(marker_data: dict[str, str]) -> dict[str, Any]:
    """Convert raw marker strings to typed values for comparison."""
    result = {}
    for key, raw in marker_data.items():
        if key in ("id", "type"):
            continue  # metadata, not syncable fields
        result[key] = coerce_value(key, raw)
    return result


def compare(md_items: dict[str, dict[str, str]], trip: Trip) -> SyncResult:
    """Compare MD marker data against Trip model.

    Args:
        md_items: {item_id: raw_marker_data} from MD files.
        trip: The Trip model loaded from JSON.

    Returns:
        SyncResult with field-level diffs and new items on each side.
    """
    result = SyncResult()

    # Build lookup of JSON items by ID
    json_attractions = {a.id: a for a in trip.attractions}
    json_day_trips = {dt.id: dt for dt in trip.day_trips}
    # Also index sub-attractions
    for dt in trip.day_trips:
        for sub in dt.sub_attractions:
            json_attractions[sub.id] = sub

    json_ids = set(json_attractions.keys()) | set(json_day_trips.keys())
    md_ids = set(md_items.keys())

    # Items only in MD
    result.new_in_md = sorted(md_ids - json_ids)

    # Items only in JSON
    result.new_in_json = sorted(json_ids - md_ids)

    # Compare items in both
    for item_id in sorted(md_ids & json_ids):
        md_data = _marker_to_syncable(md_items[item_id])
        is_day_trip = md_items[item_id].get("type") == "day_trip" or item_id in json_day_trips

        if is_day_trip and item_id in json_day_trips:
            json_obj = json_day_trips[item_id]
            sync_fields = DAY_TRIP_SYNC_FIELDS
        elif item_id in json_attractions:
            json_obj = json_attractions[item_id]
            sync_fields = ATTRACTION_SYNC_FIELDS
        else:
            continue

        # Compare each syncable field + location
        for field_name in sync_fields + ["location"]:
            md_val = md_data.get(field_name)
            json_val = _get_json_value(json_obj, field_name)

            # Normalize for comparison
            if md_val is None and json_val is None:
                continue
            if _values_equal(md_val, json_val):
                continue

            result.updates.append(FieldUpdate(
                item_id=item_id,
                field=field_name,
                md_value=md_val,
                json_value=json_val,
            ))

    return result


def apply_to_trip(result: SyncResult, trip: Trip) -> Trip:
    """Apply MD→JSON changes: update Trip model fields from MD marker values."""
    # Build lookup
    attractions_by_id = {a.id: a for a in trip.attractions}
    day_trips_by_id = {dt.id: dt for dt in trip.day_trips}
    for dt in trip.day_trips:
        for sub in dt.sub_attractions:
            attractions_by_id[sub.id] = sub

    for update in result.updates:
        obj = day_trips_by_id.get(update.item_id) or attractions_by_id.get(update.item_id)
        if obj is None:
            continue

        if update.field == "location" and update.md_value is not None:
            lat, lng, address = parse_location(str(update.md_value))
            obj.location = Location(lat=lat, lng=lng, address=address)
        else:
            _set_field(obj, update.field, update.md_value)

    # Create new attractions for items only in MD
    # (requires marker data to have enough info — at minimum name + location)
    # This is handled separately by the CLI command since we need the raw marker data

    return trip


def build_md_updates(result: SyncResult) -> dict[str, dict[str, str]]:
    """Build marker update dicts for JSON→MD sync.

    Returns {item_id: {field: new_value_str}} suitable for md_writer.update_markers.
    """
    updates: dict[str, dict[str, str]] = {}
    for update in result.updates:
        if update.item_id not in updates:
            updates[update.item_id] = {}
        val = update.json_value
        updates[update.item_id][update.field] = "null" if val is None else str(val)
    return updates


def _values_equal(a: Any, b: Any) -> bool:
    """Compare two values with type coercion tolerance."""
    if a is None and b is None:
        return True
    if a is None or b is None:
        return False
    # Compare as strings after normalizing floats
    try:
        if isinstance(a, (int, float)) and isinstance(b, (int, float)):
            return abs(float(a) - float(b)) < 0.01
        return str(a).strip() == str(b).strip()
    except (ValueError, TypeError):
        return str(a) == str(b)


def _set_field(obj: Attraction | DayTrip, field_name: str, value: Any) -> None:
    """Set a field on a model object with type coercion."""
    if not hasattr(obj, field_name):
        return
    if value is None:
        setattr(obj, field_name, None)
        return

    # Coerce to the right type based on the model field
    current = getattr(obj, field_name, None)
    if isinstance(current, float) or field_name.endswith("_eur") or field_name.endswith("_score"):
        setattr(obj, field_name, float(value))
    elif isinstance(current, int) or field_name.endswith("_minutes"):
        setattr(obj, field_name, int(float(value)))
    else:
        setattr(obj, field_name, str(value))
