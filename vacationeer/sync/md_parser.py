"""Split markdown into sections and extract @vacationeer markers."""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from vacationeer.sync.markers import MarkerMatch, find_all_markers


HEADING_PATTERN = re.compile(r"^(#{1,6})\s+(.+)$", re.MULTILINE)


@dataclass
class MdSection:
    """A markdown section delimited by headings."""

    heading: str
    heading_level: int
    body: str
    marker: dict[str, str] | None = None
    # Character span of the full section in the source text
    start: int = 0
    end: int = 0


def parse_sections(md_text: str) -> list[MdSection]:
    """Split markdown into sections by heading, attaching any @vacationeer markers."""
    headings = list(HEADING_PATTERN.finditer(md_text))
    if not headings:
        return []

    markers = find_all_markers(md_text)
    # Index markers by start position for quick lookup
    marker_by_pos = {m.start: m for m in markers}

    sections: list[MdSection] = []
    for i, match in enumerate(headings):
        heading_level = len(match.group(1))
        heading_text = match.group(2).strip()

        section_start = match.start()
        section_end = headings[i + 1].start() if i + 1 < len(headings) else len(md_text)
        body = md_text[match.end():section_end]

        # Find marker within this section's body
        section_marker = None
        for pos, marker in marker_by_pos.items():
            if section_start <= pos < section_end:
                section_marker = marker.data
                break

        sections.append(MdSection(
            heading=heading_text,
            heading_level=heading_level,
            body=body,
            marker=section_marker,
            start=section_start,
            end=section_end,
        ))

    return sections


def extract_marked_items(md_text: str) -> dict[str, dict[str, str]]:
    """Extract all @vacationeer marker data from markdown, keyed by ID.

    Returns a dict of {id: marker_data}.
    """
    markers = find_all_markers(md_text)
    items = {}
    for marker in markers:
        item_id = marker.data.get("id")
        if item_id:
            items[item_id] = marker.data
    return items


def extract_all_from_files(md_texts: dict[str, str]) -> dict[str, dict[str, str]]:
    """Extract marked items from multiple MD files.

    Args:
        md_texts: dict of {filename: md_content}

    Returns:
        dict of {id: marker_data} merged from all files.
    """
    all_items: dict[str, dict[str, str]] = {}
    for md_text in md_texts.values():
        all_items.update(extract_marked_items(md_text))
    return all_items
