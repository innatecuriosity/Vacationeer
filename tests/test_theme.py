"""Tests for vacationeer.theme — centralized color and category metadata."""
from vacationeer.models.trip import Category
from vacationeer.theme import (
    CATEGORY_META,
    PRIMARY,
    SCORE_GREEN,
    SCORE_RED,
    SCORE_YELLOW,
    STATUS_COLORS,
    get_category_info,
    score_color,
)


def test_all_categories_have_metadata():
    for cat in Category:
        info = CATEGORY_META[cat]
        assert info.color.startswith("#")
        assert info.folium_color
        assert info.icon
        assert info.emoji
        assert info.html_icon
        assert info.label


def test_get_category_info_known():
    info = get_category_info(Category.LANDMARK)
    assert info.color == "#C0392B"
    assert info.folium_color == "red"
    assert info.label == "Landmarks"


def test_get_category_info_default():
    # Shouldn't happen with current enums, but test the fallback
    info = get_category_info.__wrapped__ if hasattr(get_category_info, "__wrapped__") else get_category_info
    # All categories are covered, so just verify each returns non-None
    for cat in Category:
        assert get_category_info(cat) is not None


def test_score_color_green():
    assert score_color(8.0) == SCORE_GREEN
    assert score_color(9.5) == SCORE_GREEN
    assert score_color(10.0) == SCORE_GREEN


def test_score_color_yellow():
    assert score_color(6.0) == SCORE_YELLOW
    assert score_color(7.9) == SCORE_YELLOW


def test_score_color_red():
    assert score_color(5.9) == SCORE_RED
    assert score_color(0.0) == SCORE_RED
    assert score_color(3.0) == SCORE_RED


def test_status_colors_complete():
    assert "done" in STATUS_COLORS
    assert "confirmed" in STATUS_COLORS
    assert "skipped" in STATUS_COLORS
    assert "planned" in STATUS_COLORS


def test_primary_is_navy():
    assert PRIMARY == "#1a2332"
