"""Centralized theme constants and category metadata.

Single source of truth for colors, fonts, and category display info
used across views, maps, and templates.
"""
from __future__ import annotations

from dataclasses import dataclass

from vacationeer.models.trip import Category

# ---------------------------------------------------------------------------
# Theme palette
# ---------------------------------------------------------------------------

PRIMARY = "#1a2332"
BG_WHITE = "#ffffff"
BG_LIGHT = "#f5f6f8"
BORDER = "#d1d5db"
BORDER_LIGHT = "#e2e5e9"
TEXT_MUTED = "#888"
FONT_STACK = "system-ui,-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif"
FONT_STACK_MAP = "'Segoe UI',Roboto,Arial,sans-serif"

# ---------------------------------------------------------------------------
# Score colors
# ---------------------------------------------------------------------------

SCORE_GREEN = "#27AE60"
SCORE_YELLOW = "#F1C40F"
SCORE_RED = "#E74C3C"


def score_color(score: float) -> str:
    if score >= 8:
        return SCORE_GREEN
    if score >= 6:
        return SCORE_YELLOW
    return SCORE_RED


# ---------------------------------------------------------------------------
# Activity status colors
# ---------------------------------------------------------------------------

STATUS_COLORS: dict[str, str] = {
    "done": "#27ae60",
    "confirmed": "#3498db",
    "skipped": "#bbb",
    "planned": "#f39c12",
}

# ---------------------------------------------------------------------------
# Category metadata
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CategoryInfo:
    color: str
    folium_color: str
    icon: str
    emoji: str
    html_icon: str
    label: str


CATEGORY_META: dict[Category, CategoryInfo] = {
    Category.LANDMARK: CategoryInfo(
        color="#C0392B", folium_color="red",
        icon="university", emoji="\U0001F3DB",
        html_icon="&#x1f3db;", label="Landmarks",
    ),
    Category.MUSEUM: CategoryInfo(
        color="#2980B9", folium_color="blue",
        icon="info-sign", emoji="\U0001F5BC",
        html_icon="&#x1f5bc;", label="Museums",
    ),
    Category.NATURE: CategoryInfo(
        color="#27AE60", folium_color="green",
        icon="tree-deciduous", emoji="\U0001F333",
        html_icon="&#x1f333;", label="Nature",
    ),
    Category.FOOD: CategoryInfo(
        color="#E67E22", folium_color="orange",
        icon="cutlery", emoji="\U0001F37D",
        html_icon="&#x1f374;", label="Food",
    ),
    Category.ENTERTAINMENT: CategoryInfo(
        color="#8E44AD", folium_color="purple",
        icon="star", emoji="\U0001F3AD",
        html_icon="&#x1f3ad;", label="Entertainment",
    ),
    Category.TRANSPORT: CategoryInfo(
        color="#7F8C8D", folium_color="gray",
        icon="road", emoji="\U0001F68C",
        html_icon="&#x1f68c;", label="Transport",
    ),
    Category.ACCOMMODATION: CategoryInfo(
        color="#922B21", folium_color="darkred",
        icon="home", emoji="\U0001F3E8",
        html_icon="&#x1f3e8;", label="Accommodation",
    ),
    Category.SHOPPING: CategoryInfo(
        color="#2E86C1", folium_color="cadetblue",
        icon="shopping-cart", emoji="\U0001F6CD",
        html_icon="&#x1f6cd;", label="Shopping",
    ),
    Category.DAY_TRIP: CategoryInfo(
        color="#1E8449", folium_color="darkgreen",
        icon="globe", emoji="\U0001F30D",
        html_icon="&#x1f697;", label="Day Trips",
    ),
    Category.INFRASTRUCTURE: CategoryInfo(
        color="#34495E", folium_color="darkblue",
        icon="tower", emoji="\u2708",
        html_icon="&#x2708;", label="Infrastructure",
    ),
}

_DEFAULT_INFO = CategoryInfo(
    color="#7F8C8D", folium_color="gray",
    icon="info-sign", emoji="\u2139",
    html_icon="&#x2139;", label="Other",
)


def get_category_info(cat: Category) -> CategoryInfo:
    return CATEGORY_META.get(cat, _DEFAULT_INFO)
