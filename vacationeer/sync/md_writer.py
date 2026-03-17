"""Surgically update or inject @vacationeer marker blocks in markdown text."""
from __future__ import annotations

import difflib
import re

from vacationeer.sync.markers import (
    MARKER_PATTERN,
    find_all_markers,
    render_marker,
)
from vacationeer.sync.md_parser import parse_sections


def update_markers(md_text: str, updates: dict[str, dict[str, str]]) -> str:
    """Update existing @vacationeer blocks in-place by item ID.

    Args:
        md_text: The full markdown text.
        updates: {item_id: {field: new_value, ...}} — only changed fields.

    Returns:
        Updated markdown text. Narrative content is untouched.
    """
    markers = find_all_markers(md_text)

    # Process in reverse order so position offsets stay valid
    for marker in reversed(markers):
        item_id = marker.data.get("id")
        if item_id not in updates:
            continue

        # Merge updates into existing data
        new_data = dict(marker.data)
        new_data.update(updates[item_id])

        new_block = render_marker(new_data)
        md_text = md_text[:marker.start] + new_block + md_text[marker.end:]

    return md_text


MIN_MATCH_RATIO = 0.55


def inject_marker(
    md_text: str,
    section_heading: str,
    marker_data: dict[str, str],
) -> tuple[str, bool]:
    """Inject a new @vacationeer block at the end of the section matching the heading.

    Uses fuzzy matching to find the best heading match. Returns (text, injected).
    If no good match is found, returns the original text unchanged.
    """
    sections = parse_sections(md_text)
    if not sections:
        return md_text, False

    # Find best matching section by heading text
    best_section = None
    best_ratio = 0.0
    target = _normalize(section_heading)

    for section in sections:
        ratio = difflib.SequenceMatcher(
            None, target, _normalize(section.heading)
        ).ratio()
        if ratio > best_ratio:
            best_ratio = ratio
            best_section = section

    if best_section is None or best_ratio < MIN_MATCH_RATIO:
        return md_text, False

    # Insert before the end of the matched section
    insert_pos = best_section.end
    # Back up past trailing whitespace to keep formatting clean
    while insert_pos > best_section.start and md_text[insert_pos - 1] in ("\n", " "):
        insert_pos -= 1

    block = render_marker(marker_data)
    md_text = md_text[:insert_pos] + "\n\n" + block + "\n" + md_text[insert_pos:]
    return md_text, True


def inject_all_markers(
    md_text: str,
    items: list[dict[str, str]],
    heading_names: dict[str, str] | None = None,
) -> tuple[str, list[str]]:
    """Inject @vacationeer blocks for multiple items into markdown text.

    Only injects if a good heading match is found (fuzzy ratio >= 0.55).

    Args:
        md_text: The full markdown text.
        items: List of marker data dicts (each must have 'id' and 'name').
        heading_names: Optional {item_id: heading_to_match}. If not provided,
                       uses the item's 'name' field.

    Returns:
        (updated_text, injected_ids) — the updated markdown and list of IDs that were injected.
    """
    # Check which IDs already have markers
    existing = find_all_markers(md_text)
    existing_ids = {m.data.get("id") for m in existing}
    injected_ids = []

    for item in items:
        item_id = item.get("id", "")
        if item_id in existing_ids:
            continue  # Already has a marker

        heading = (heading_names or {}).get(item_id, item.get("name", ""))
        if not heading:
            continue

        md_text, was_injected = inject_marker(md_text, heading, item)
        if was_injected:
            injected_ids.append(item_id)
            existing_ids.add(item_id)

    return md_text, injected_ids


def _normalize(text: str) -> str:
    """Normalize heading text for fuzzy matching."""
    # Remove markdown formatting
    text = re.sub(r"[*_`#\[\]()]", "", text)
    # Remove common prefixes like "MUST-DO:", "3.1", numbering
    text = re.sub(r"^[\d.]+\s*", "", text)
    text = re.sub(r"^MUST-DO:\s*", "", text, flags=re.IGNORECASE)
    # Remove subtitle after em-dash/dash
    text = re.sub(r"\s*[—–-]{1,2}\s+.*$", "", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip().lower()


def best_match_ratio(item_name: str, md_text: str) -> float:
    """Return the best fuzzy match ratio for an item name against any heading in the text."""
    sections = parse_sections(md_text)
    target = _normalize(item_name)
    best = 0.0
    for section in sections:
        ratio = difflib.SequenceMatcher(
            None, target, _normalize(section.heading)
        ).ratio()
        if ratio > best:
            best = ratio
    return best
