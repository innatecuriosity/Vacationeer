from __future__ import annotations

import json
from pathlib import Path

from vacationeer.models.trip import Trip


class JsonTripStore:
    """JSON-file backed trip storage."""

    def __init__(self, path: Path) -> None:
        self._path = path

    def load(self) -> Trip:
        data = json.loads(self._path.read_text(encoding="utf-8"))
        return Trip.model_validate(data)

    def save(self, trip: Trip) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(trip.model_dump_json(indent=2), encoding="utf-8")


# Backward-compatible bare functions
def save_trip(trip: Trip, path: Path) -> None:
    JsonTripStore(path).save(trip)


def load_trip(path: Path) -> Trip:
    return JsonTripStore(path).load()
