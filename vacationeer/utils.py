"""Shared utility functions for the vacationeer package."""
from __future__ import annotations

import re


def slugify(name: str) -> str:
    """Convert a name to a URL-friendly slug id."""
    slug = name.lower().strip()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[\s_]+", "-", slug)
    slug = re.sub(r"-+", "-", slug).strip("-")
    return slug
