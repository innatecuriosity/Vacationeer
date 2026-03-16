from __future__ import annotations

import json
from pathlib import Path

from vacationeer.models.trip import Trip


def save_trip(trip: Trip, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(trip.model_dump_json(indent=2), encoding="utf-8")


def load_trip(path: Path) -> Trip:
    data = json.loads(path.read_text(encoding="utf-8"))
    return Trip.model_validate(data)
