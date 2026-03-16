from __future__ import annotations

from pathlib import Path

import folium
from branca.element import MacroElement
from jinja2 import Template

from vacationeer.models.trip import Attraction, Category, Trip

# Category → (marker color, hex color, icon, unicode icon for legend)
CATEGORY_STYLE: dict[Category, tuple[str, str, str, str]] = {
    Category.LANDMARK:      ("red",       "#C0392B", "university",    "\U0001F3DB"),
    Category.MUSEUM:        ("blue",      "#2980B9", "info-sign",     "\U0001F3DB"),
    Category.NATURE:        ("green",     "#27AE60", "tree-deciduous","\U0001F333"),
    Category.FOOD:          ("orange",    "#E67E22", "cutlery",       "\U0001F37D"),
    Category.ENTERTAINMENT: ("purple",    "#8E44AD", "star",          "\U0001F3AD"),
    Category.TRANSPORT:     ("gray",      "#7F8C8D", "road",          "\U0001F68C"),
    Category.ACCOMMODATION: ("darkred",   "#922B21", "home",          "\U0001F3E8"),
    Category.SHOPPING:      ("cadetblue", "#2E86C1", "shopping-cart", "\U0001F6CD"),
    Category.DAY_TRIP:      ("darkgreen", "#1E8449", "globe",         "\U0001F30D"),
}


def _popup_html(a: Attraction) -> str:
    """Build a styled popup card for an attraction."""
    color, hex_color, _, _ = CATEGORY_STYLE.get(
        a.category, ("gray", "#7F8C8D", "info-sign", "\u2139")
    )
    category_label = a.category.value.replace("_", " ").title()

    # --- header ---
    html = f"""
<div style="font-family:'Segoe UI',Roboto,Arial,sans-serif;width:260px;border-radius:10px;overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,.15);">
  <div style="background:{hex_color};color:#fff;padding:10px 14px;">
    <div style="font-size:9px;text-transform:uppercase;letter-spacing:1px;opacity:.85;">{category_label}</div>
    <div style="font-size:15px;font-weight:700;margin-top:2px;">{a.name}</div>
  </div>
  <div style="padding:10px 14px;background:#fff;color:#333;font-size:12px;line-height:1.5;">
"""

    # --- description ---
    if a.description:
        html += f'<div style="color:#555;margin-bottom:8px;">{a.description}</div>'

    # --- price + duration row ---
    badges = []
    if a.price_eur is not None:
        if a.price_eur == 0:
            badge_text = "FREE"
            badge_bg = "#27AE60"
        else:
            badge_text = f"\u20AC{a.price_eur:.0f}"
            badge_bg = hex_color
        badges.append(
            f'<span style="display:inline-block;background:{badge_bg};color:#fff;'
            f'padding:2px 9px;border-radius:12px;font-size:11px;font-weight:600;">'
            f'{badge_text}</span>'
        )
    if a.duration_minutes:
        h, m = divmod(a.duration_minutes, 60)
        dur = f"{h}h{m:02d}" if h else f"{m} min"
        badges.append(
            f'<span style="display:inline-block;color:#555;font-size:11px;">'
            f'\U0001F552 {dur}</span>'
        )
    if badges:
        html += f'<div style="margin-bottom:8px;display:flex;align-items:center;gap:8px;">{"".join(badges)}</div>'

    # --- tags ---
    if a.tags:
        tag_pills = "".join(
            f'<span style="display:inline-block;background:{hex_color}18;color:{hex_color};'
            f'padding:1px 7px;border-radius:8px;font-size:10px;margin:2px 3px 2px 0;'
            f'border:1px solid {hex_color}40;">{t}</span>'
            for t in a.tags
        )
        html += f'<div style="margin-bottom:8px;">{tag_pills}</div>'

    # --- tips ---
    if a.tips:
        html += (
            f'<div style="background:#FFF9E6;border-left:3px solid #F1C40F;'
            f'padding:6px 10px;border-radius:0 6px 6px 0;margin-bottom:8px;'
            f'font-size:11px;color:#7D6608;">'
            f'\U0001F4A1 <b>Tip:</b> {a.tips}</div>'
        )

    # --- url button ---
    if a.url:
        html += (
            f'<a href="{a.url}" target="_blank" style="display:inline-block;'
            f'background:{hex_color};color:#fff;text-decoration:none;'
            f'padding:5px 14px;border-radius:6px;font-size:11px;font-weight:600;'
            f'letter-spacing:.3px;">Visit website \u2197</a>'
        )

    html += """
  </div>
</div>
"""
    return html


class _Legend(MacroElement):
    """A custom legend overlay for the bottom-left corner of the map."""

    _template = Template("""
{% macro header(this, kwargs) %}{% endmacro %}
{% macro html(this, kwargs) %}
<div id="legend-box" style="
    position:fixed;bottom:28px;left:12px;z-index:1000;
    background:rgba(255,255,255,.92);backdrop-filter:blur(4px);
    border-radius:10px;padding:12px 16px;
    box-shadow:0 2px 10px rgba(0,0,0,.18);font-family:'Segoe UI',Roboto,Arial,sans-serif;
    font-size:12px;max-height:50vh;overflow-y:auto;">
  <div style="font-weight:700;margin-bottom:6px;font-size:13px;color:#333;">Categories</div>
  {% for item in this.items %}
  <div style="display:flex;align-items:center;gap:6px;padding:2px 0;">
    <span style="font-size:15px;">{{ item.icon }}</span>
    <span style="display:inline-block;width:10px;height:10px;border-radius:50%;background:{{ item.hex }}"></span>
    <span style="color:#444;">{{ item.label }}</span>
  </div>
  {% endfor %}
</div>
{% endmacro %}
""")

    def __init__(self, items: list[dict]):
        super().__init__()
        self.items = items


def generate_map(trip: Trip, output_path: Path) -> Path:
    if not trip.attractions:
        raise ValueError("Trip has no attractions to map")

    # Center on average of all attraction coordinates
    avg_lat = sum(a.location.lat for a in trip.attractions) / len(trip.attractions)
    avg_lng = sum(a.location.lng for a in trip.attractions) / len(trip.attractions)

    m = folium.Map(
        location=[avg_lat, avg_lng],
        zoom_start=13,
        tiles="CartoDB Voyager",
    )

    # Create a feature group per category for layer toggling
    groups: dict[Category, folium.FeatureGroup] = {}
    for cat in Category:
        fg = folium.FeatureGroup(name=cat.value.replace("_", " ").title())
        groups[cat] = fg

    for attraction in trip.attractions:
        color, hex_color, icon, _ = CATEGORY_STYLE.get(
            attraction.category, ("gray", "#7F8C8D", "info-sign", "\u2139")
        )
        category_label = attraction.category.value.replace("_", " ").title()
        tooltip_text = f"{category_label} \u2022 {attraction.name}"

        marker = folium.Marker(
            location=[attraction.location.lat, attraction.location.lng],
            popup=folium.Popup(_popup_html(attraction), max_width=280),
            tooltip=tooltip_text,
            icon=folium.Icon(color=color, icon=icon, prefix="glyphicon"),
        )
        marker.add_to(groups[attraction.category])

    # Only add groups that have markers
    used_categories: list[Category] = []
    for cat, fg in groups.items():
        if any(True for _ in fg._children.values()):
            fg.add_to(m)
            used_categories.append(cat)

    folium.LayerControl(collapsed=False).add_to(m)

    # Add legend for used categories
    legend_items = []
    for cat in used_categories:
        _, hex_color, _, unicode_icon = CATEGORY_STYLE.get(
            cat, ("gray", "#7F8C8D", "info-sign", "\u2139")
        )
        legend_items.append({
            "icon": unicode_icon,
            "hex": hex_color,
            "label": cat.value.replace("_", " ").title(),
        })
    _Legend(items=legend_items).add_to(m)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    m.save(str(output_path))
    return output_path
