"""Shared view utility functions used across HTML generation modules."""
from __future__ import annotations

from datetime import time

from vacationeer.models.trip import Category
from vacationeer.theme import CATEGORY_META


def esc(text: str | None) -> str:
    if text is None:
        return ""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def format_price(price: float | None) -> str:
    if price is None:
        return ""
    if price == 0:
        return "Free"
    return f"\u20ac{price:.0f}" if price == int(price) else f"\u20ac{price:.2f}"


def format_time(t: time | None) -> str:
    if t is None:
        return ""
    return t.strftime("%H:%M")


def format_duration(minutes: int | None) -> str:
    if minutes is None:
        return ""
    if minutes < 60:
        return f"{minutes}min"
    h, m = divmod(minutes, 60)
    return f"{h}h {m}min" if m else f"{h}h"


def category_label(cat: Category) -> str:
    info = CATEGORY_META.get(cat)
    if info:
        return info.label
    return cat.value.replace("_", " ").title()
