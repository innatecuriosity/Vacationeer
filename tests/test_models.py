"""Tests for vacationeer.models.trip — Pydantic models."""
from datetime import date

from vacationeer.models.trip import (
    Attraction,
    Category,
    DayTrip,
    Location,
    Preferences,
    Trip,
)


def _make_trip(**kwargs) -> Trip:
    defaults = dict(
        name="Test Trip",
        destination="Valencia",
        start_date=date(2026, 3, 21),
        end_date=date(2026, 3, 28),
    )
    defaults.update(kwargs)
    return Trip(**defaults)


class TestDestSlug:
    def test_simple(self):
        trip = _make_trip(destination="Valencia")
        assert trip.dest_slug == "valencia"

    def test_multi_word(self):
        trip = _make_trip(destination="New York City")
        assert trip.dest_slug == "new-york-city"

    def test_already_lowercase(self):
        trip = _make_trip(destination="rome")
        assert trip.dest_slug == "rome"

    def test_dest_slug_not_serialized(self):
        trip = _make_trip(destination="Valencia")
        data = trip.model_dump()
        assert "dest_slug" not in data


class TestTripModel:
    def test_default_travelers(self):
        trip = _make_trip()
        assert trip.travelers == 2

    def test_empty_collections(self):
        trip = _make_trip()
        assert trip.attractions == []
        assert trip.day_trips == []
        assert trip.days == []

    def test_id_auto_generated(self):
        trip = _make_trip()
        assert len(trip.id) == 8


class TestAttractionModel:
    def test_minimal(self):
        a = Attraction(
            name="Test",
            location=Location(lat=39.47, lng=-0.37),
            category=Category.LANDMARK,
        )
        assert a.name == "Test"
        assert a.price_eur is None
        assert a.user_score is None

    def test_id_auto_generated(self):
        a = Attraction(
            name="Test",
            location=Location(lat=39.47, lng=-0.37),
            category=Category.LANDMARK,
        )
        assert len(a.id) == 8
