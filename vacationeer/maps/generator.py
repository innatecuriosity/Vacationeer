from __future__ import annotations

from pathlib import Path

import folium
from folium.plugins import MarkerCluster

from vacationeer.models.trip import Attraction, Category, Trip

# Category → (color, icon)
CATEGORY_STYLE: dict[Category, tuple[str, str]] = {
    Category.LANDMARK: ("red", "university"),
    Category.MUSEUM: ("blue", "info-sign"),
    Category.NATURE: ("green", "tree-deciduous"),
    Category.FOOD: ("orange", "cutlery"),
    Category.ENTERTAINMENT: ("purple", "star"),
    Category.TRANSPORT: ("gray", "road"),
    Category.ACCOMMODATION: ("darkred", "home"),
    Category.SHOPPING: ("cadetblue", "shopping-cart"),
    Category.DAY_TRIP: ("darkgreen", "globe"),
}


def _popup_html(a: Attraction) -> str:
    lines = [f"<b>{a.name}</b>"]
    if a.description:
        lines.append(f"<br><i>{a.description}</i>")
    if a.price_eur is not None:
        lines.append(f"<br>Price: {a.price_eur:.0f} EUR")
    if a.duration_minutes:
        h, m = divmod(a.duration_minutes, 60)
        dur = f"{h}h{m:02d}" if h else f"{m} min"
        lines.append(f"<br>Duration: {dur}")
    if a.tips:
        lines.append(f"<br><small>{a.tips}</small>")
    if a.url:
        lines.append(f'<br><a href="{a.url}" target="_blank">Website</a>')
    if a.tags:
        lines.append(f"<br><small>Tags: {', '.join(a.tags)}</small>")
    return "".join(lines)


def generate_map(trip: Trip, output_path: Path) -> Path:
    if not trip.attractions:
        raise ValueError("Trip has no attractions to map")

    # Center on average of all attraction coordinates
    avg_lat = sum(a.location.lat for a in trip.attractions) / len(trip.attractions)
    avg_lng = sum(a.location.lng for a in trip.attractions) / len(trip.attractions)

    m = folium.Map(
        location=[avg_lat, avg_lng],
        zoom_start=13,
        tiles="CartoDB Positron",
    )

    # Create a feature group per category for layer toggling
    groups: dict[Category, folium.FeatureGroup] = {}
    for cat in Category:
        fg = folium.FeatureGroup(name=cat.value.replace("_", " ").title())
        groups[cat] = fg

    for attraction in trip.attractions:
        color, icon = CATEGORY_STYLE.get(attraction.category, ("gray", "info-sign"))
        marker = folium.Marker(
            location=[attraction.location.lat, attraction.location.lng],
            popup=folium.Popup(_popup_html(attraction), max_width=300),
            tooltip=attraction.name,
            icon=folium.Icon(color=color, icon=icon, prefix="glyphicon"),
        )
        marker.add_to(groups[attraction.category])

    # Only add groups that have markers
    for cat, fg in groups.items():
        if any(True for _ in fg._children.values()):
            fg.add_to(m)

    folium.LayerControl(collapsed=False).add_to(m)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    m.save(str(output_path))
    return output_path
