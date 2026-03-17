from __future__ import annotations

import statistics
from pathlib import Path

import folium
from branca.element import MacroElement
from folium.plugins import MarkerCluster
from jinja2 import Template

from vacationeer.models.trip import Attraction, Category, Trip
from vacationeer.theme import CATEGORY_META, FONT_STACK_MAP, get_category_info
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


def _marker_html(emoji: str, name: str) -> str:
    """Emoji icon with name label below — single DivIcon, no overlap."""
    return (
        f'<div style="display:flex;flex-direction:column;align-items:center;pointer-events:auto;">'
        f'<div style="font-size:22px;line-height:1;'
        f'filter:drop-shadow(0 1px 2px rgba(0,0,0,0.3));">{emoji}</div>'
        f'<div style="font-family:\'{FONT_STACK_MAP}\';font-size:9px;font-weight:600;'
        f'color:#222;text-align:center;max-width:80px;overflow:hidden;text-overflow:ellipsis;'
        f'white-space:nowrap;line-height:1.1;margin-top:1px;'
        f'text-shadow:0 0 3px #fff,0 0 3px #fff,1px 1px 2px #fff,-1px -1px 2px #fff;'
        f'">{name}</div>'
        f'</div>'
    )


class _ControlStyle(MacroElement):
    """Custom CSS to style the Leaflet layer control and MarkerCluster."""

    _template = Template("""
{% macro header(this, kwargs) %}
<style>
    .leaflet-control-layers {
        border-radius: 12px !important;
        padding: 14px 18px !important;
        box-shadow: 0 2px 12px rgba(0,0,0,.2) !important;
        font-family: 'Segoe UI', Roboto, Arial, sans-serif !important;
        font-size: 13px !important;
        background: rgba(255,255,255,.95) !important;
        backdrop-filter: blur(4px);
        border: none !important;
        min-width: 180px;
    }
    .leaflet-control-layers-overlays label {
        display: flex !important;
        align-items: center !important;
        gap: 6px !important;
        padding: 3px 0 !important;
        margin: 0 !important;
        cursor: pointer;
    }
    .leaflet-control-layers-overlays label span {
        font-size: 13px;
    }
    .leaflet-control-layers-separator {
        border-top: 1px solid #e0e0e0 !important;
        margin: 6px 0 !important;
    }
    .leaflet-control-layers-toggle {
        width: 36px !important;
        height: 36px !important;
    }
    /* MarkerCluster custom styling */
    .marker-cluster {
        background: rgba(255,255,255,0.85) !important;
        border: 2px solid #1a2332 !important;
        border-radius: 50% !important;
        box-shadow: 0 2px 8px rgba(0,0,0,0.2);
    }
    .marker-cluster div {
        background: #1a2332 !important;
        color: #fff !important;
        font-weight: 700;
        font-size: 13px;
        border-radius: 50%;
        width: 30px !important;
        height: 30px !important;
        margin: 3px !important;
        line-height: 30px !important;
        text-align: center;
    }
    .marker-cluster-small {
        background: rgba(255,255,255,0.85) !important;
    }
    .marker-cluster-medium {
        background: rgba(255,255,255,0.85) !important;
    }
    .marker-cluster-large {
        background: rgba(255,255,255,0.85) !important;
    }
</style>
{% endmacro %}
""")


def generate_map(trip: Trip, output_path: Path) -> Path:
    if not trip.attractions:
        raise ValueError("Trip has no attractions to map")

    # Filter out coordinate outliers (e.g. 0,0) before computing center
    valid = [a for a in trip.attractions if not (abs(a.location.lat) < 0.01 and abs(a.location.lng) < 0.01)]
    if not valid:
        valid = trip.attractions

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

    # MarkerCluster groups nearby markers when zoomed out
    cluster = MarkerCluster(
        options={
            "maxClusterRadius": 40,
            "spiderfyOnMaxZoom": True,
            "disableClusteringAtZoom": 15,
            "showCoverageOnHover": False,
        },
    )

    # Create a feature group per category — ALL categories, even if empty
    groups: dict[Category, folium.FeatureGroup] = {}
    for cat in Category:
        info = get_category_info(cat)
        fg = folium.FeatureGroup(name=f"{info.html_icon} {info.label}")
        groups[cat] = fg

    for attraction in trip.attractions:
        info = get_category_info(attraction.category)

        popup_html = _popup_html(attraction)
        tooltip_html = _tooltip_html(attraction)

        # Combined emoji + label in a single DivIcon (label sits below emoji)
        marker = folium.Marker(
            location=[attraction.location.lat, attraction.location.lng],
            icon=folium.DivIcon(
                html=_marker_html(info.emoji, attraction.name),
                icon_size=(80, 40),
                icon_anchor=(40, 14),
            ),
            tooltip=folium.Tooltip(tooltip_html, sticky=False),
            popup=folium.Popup(popup_html, max_width=320),
        )
        marker.add_to(groups[attraction.category])

    # Add ALL groups to the cluster (even empty ones go directly to map for layer control)
    for cat, fg in groups.items():
        if any(True for _ in fg._children.values()):
            # Groups with markers go through the cluster
            fg.add_to(cluster)
        else:
            # Empty groups go directly to map so they appear in layer control
            fg.add_to(m)

    cluster.add_to(m)

    # Unified layer control (top-right)
    folium.LayerControl(collapsed=False, position='topright').add_to(m)

    # Custom CSS
    _ControlStyle().add_to(m)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    m.save(str(output_path))
    return output_path
