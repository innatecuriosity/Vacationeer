from __future__ import annotations

import statistics
from pathlib import Path

import folium
from branca.element import MacroElement
from jinja2 import Template

from vacationeer.models.trip import Attraction, Category, Trip
from vacationeer.theme import FONT_STACK_MAP, get_category_info
from vacationeer.views.helpers import category_label


def _popup_html(a: Attraction) -> str:
    """Build a styled popup card for an attraction."""
    info = get_category_info(a.category)
    hex_color = info.color

    # --- header ---
    html = f"""
<div style="font-family:{FONT_STACK_MAP};width:260px;border-radius:10px;overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,.15);">
  <div style="background:{hex_color};color:#fff;padding:10px 14px;">
    <div style="font-size:9px;text-transform:uppercase;letter-spacing:1px;opacity:.85;">{category_label(a.category)}</div>
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


def _tooltip_html(a: Attraction) -> str:
    """Build a short hover tooltip for an attraction."""
    info = get_category_info(a.category)
    hex_color = info.color
    return (
        f'<div style="font-family:\'{FONT_STACK_MAP}\';font-size:11px;line-height:1.4;">'
        f'<b>{a.name}</b><br>'
        f'<span style="color:{hex_color};font-weight:600;">{category_label(a.category)}</span>'
        f'</div>'
    )


class _Legend(MacroElement):
    """A custom legend overlay for the bottom-left corner of the map."""

    _template = Template("""
{% macro header(this, kwargs) %}{% endmacro %}
{% macro html(this, kwargs) %}
<div id="legend-box" style="
    position:fixed;bottom:28px;left:12px;z-index:1000;
    background:rgba(255,255,255,.95);backdrop-filter:blur(4px);
    border-radius:12px;padding:16px 22px;
    box-shadow:0 2px 12px rgba(0,0,0,.2);font-family:'Segoe UI',Roboto,Arial,sans-serif;
    font-size:14px;max-height:55vh;overflow-y:auto;min-width:180px;">
  <div style="font-weight:700;margin-bottom:8px;font-size:15px;color:#222;">Categories</div>
  {% for item in this.items %}
  <div style="display:flex;align-items:center;gap:8px;padding:3px 0;">
    <span style="font-size:17px;">{{ item.icon }}</span>
    <span style="display:inline-block;width:12px;height:12px;border-radius:50%;background:{{ item.hex }};flex-shrink:0;"></span>
    <span style="color:#333;font-size:14px;">{{ item.label }}</span>
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

    # Filter out coordinate outliers (e.g. 0,0) before computing center
    valid = [a for a in trip.attractions if not (abs(a.location.lat) < 0.01 and abs(a.location.lng) < 0.01)]
    if not valid:
        valid = trip.attractions  # fallback to all if everything is "invalid"

    # Use median-based filtering: exclude points > 2 degrees from median
    med_lat = statistics.median(a.location.lat for a in valid)
    med_lng = statistics.median(a.location.lng for a in valid)
    nearby = [a for a in valid if abs(a.location.lat - med_lat) < 2 and abs(a.location.lng - med_lng) < 2]
    if not nearby:
        nearby = valid

    avg_lat = sum(a.location.lat for a in nearby) / len(nearby)
    avg_lng = sum(a.location.lng for a in nearby) / len(nearby)

    m = folium.Map(
        location=[avg_lat, avg_lng],
        zoom_start=13,
        tiles="CartoDB Voyager",
    )

    # Create a feature group per category for layer toggling
    groups: dict[Category, folium.FeatureGroup] = {}
    for cat in Category:
        fg = folium.FeatureGroup(name=category_label(cat))
        groups[cat] = fg


    for attraction in trip.attractions:
        info = get_category_info(attraction.category)
        hex_color = info.color

        popup_html = _popup_html(attraction)
        tooltip_html = _tooltip_html(attraction)

        if attraction.category == Category.ACCOMMODATION:
            marker = folium.Marker(
                location=[attraction.location.lat, attraction.location.lng],
                icon=folium.DivIcon(
                    html='<div style="font-size:24px;text-align:center;line-height:1;filter:drop-shadow(0 1px 2px rgba(0,0,0,0.3));">\U0001f3e0</div>',
                    icon_size=(30, 30),
                    icon_anchor=(15, 15),
                ),
                tooltip=folium.Tooltip(tooltip_html, sticky=False),
                popup=folium.Popup(popup_html, max_width=320),
            )
        elif attraction.category == Category.LANDMARK:
            marker = folium.Marker(
                location=[attraction.location.lat, attraction.location.lng],
                icon=folium.DivIcon(
                    html='<div style="font-size:22px;text-align:center;line-height:1;filter:drop-shadow(0 1px 2px rgba(0,0,0,0.3));">\U0001f3db</div>',
                    icon_size=(28, 28),
                    icon_anchor=(14, 14),
                ),
                tooltip=folium.Tooltip(tooltip_html, sticky=False),
                popup=folium.Popup(popup_html, max_width=320),
            )
        elif attraction.category == Category.INFRASTRUCTURE:
            marker = folium.Marker(
                location=[attraction.location.lat, attraction.location.lng],
                icon=folium.DivIcon(
                    html='<div style="font-size:22px;text-align:center;line-height:1;filter:drop-shadow(0 1px 2px rgba(0,0,0,0.3));">\u2708</div>',
                    icon_size=(28, 28),
                    icon_anchor=(14, 14),
                ),
                tooltip=folium.Tooltip(tooltip_html, sticky=False),
                popup=folium.Popup(popup_html, max_width=320),
            )
        else:
            marker = folium.CircleMarker(
                location=[attraction.location.lat, attraction.location.lng],
                radius=8,
                color=hex_color,
                weight=2,
                fill=True,
                fill_color=hex_color,
                fill_opacity=0.75,
                tooltip=folium.Tooltip(tooltip_html, sticky=False),
                popup=folium.Popup(popup_html, max_width=320),
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
        info = get_category_info(cat)
        legend_items.append({
            "icon": info.emoji,
            "hex": info.color,
            "label": info.label,
        })
    _Legend(items=legend_items).add_to(m)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    m.save(str(output_path))
    return output_path
