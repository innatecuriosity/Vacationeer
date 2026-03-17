from __future__ import annotations

from typing import Protocol, runtime_checkable

from vacationeer.models.trip import Trip


@runtime_checkable
class TripStore(Protocol):
    def load(self) -> Trip: ...
    def save(self, trip: Trip) -> None: ...
