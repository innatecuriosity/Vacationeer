"""Tests for vacationeer.views.helpers — shared view utility functions."""
from datetime import time

from vacationeer.models.trip import Category
from vacationeer.views.helpers import (
    category_label,
    esc,
    format_duration,
    format_price,
    format_time,
)


class TestEsc:
    def test_none(self):
        assert esc(None) == ""

    def test_plain_text(self):
        assert esc("hello") == "hello"

    def test_html_entities(self):
        assert esc('<script>alert("xss")</script>') == (
            "&lt;script&gt;alert(&quot;xss&quot;)&lt;/script&gt;"
        )

    def test_ampersand(self):
        assert esc("A & B") == "A &amp; B"


class TestFormatPrice:
    def test_none(self):
        assert format_price(None) == ""

    def test_free(self):
        assert format_price(0) == "Free"
        assert format_price(0.0) == "Free"

    def test_integer_price(self):
        assert format_price(10.0) == "\u20ac10"

    def test_decimal_price(self):
        assert format_price(10.50) == "\u20ac10.50"


class TestFormatTime:
    def test_none(self):
        assert format_time(None) == ""

    def test_time(self):
        assert format_time(time(9, 30)) == "09:30"
        assert format_time(time(14, 0)) == "14:00"


class TestFormatDuration:
    def test_none(self):
        assert format_duration(None) == ""

    def test_minutes_only(self):
        assert format_duration(45) == "45min"

    def test_hours_only(self):
        assert format_duration(120) == "2h"

    def test_hours_and_minutes(self):
        assert format_duration(90) == "1h 30min"


class TestCategoryLabel:
    def test_known_categories(self):
        assert category_label(Category.LANDMARK) == "Landmarks"
        assert category_label(Category.DAY_TRIP) == "Day Trips"
        assert category_label(Category.FOOD) == "Food"

    def test_all_categories(self):
        for cat in Category:
            label = category_label(cat)
            assert isinstance(label, str)
            assert len(label) > 0
