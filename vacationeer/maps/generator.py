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
    """Build a styled popup card for an attraction with inline editing."""
    info = get_category_info(a.category)
    hex_color = info.color
    uid = a.id  # unique id for this popup's form elements

    h, m = divmod(a.duration_minutes or 0, 60)
    dur = f"{h}h{m:02d}" if h else f"{m} min" if a.duration_minutes else ""
    price_text = "Free" if a.price_eur == 0 else f"\u20AC{a.price_eur:.0f}" if a.price_eur else ""
    score_text = f"{a.expected_score:.1f}" if a.expected_score is not None else ""

    # Tags
    tag_pills = ""
    if a.tags:
        tag_pills = '<div style="margin-top:8px;display:flex;flex-wrap:wrap;gap:3px;">' + "".join(
            f'<span style="display:inline-block;background:{hex_color}18;color:{hex_color};'
            f'padding:1px 7px;border-radius:8px;font-size:10px;'
            f'border:1px solid {hex_color}40;">{t}</span>'
            for t in a.tags
        ) + '</div>'

    # Tips
    tips_html = ""
    if a.tips:
        tips_html = (
            f'<div style="background:#FFF9E6;border-left:3px solid #F1C40F;'
            f'padding:6px 10px;border-radius:0 6px 6px 0;margin-top:8px;'
            f'font-size:11px;color:#7D6608;">'
            f'\U0001F4A1 <b>Tip:</b> {a.tips}</div>'
        )

    # URL
    url_html = ""
    if a.url:
        url_html = (
            f'<a href="{a.url}" target="_blank" style="display:inline-block;'
            f'background:{hex_color};color:#fff;text-decoration:none;'
            f'padding:4px 12px;border-radius:6px;font-size:11px;font-weight:600;'
            f'margin-top:8px;">Website \u2197</a>'
        )

    # Star rating HTML (display-only, no script tags allowed in folium popups)
    user_score = a.user_score or 0
    stars_html = ""
    for s in range(1, 11):
        filled = "#f39c12" if s <= user_score else "#ddd"
        stars_html += f'<span style="font-size:14px;color:{filled};">&#x2605;</span>'

    desc_html = ""
    if a.description:
        desc_html = f'<div style="color:#555;font-size:12px;line-height:1.5;margin-bottom:8px;">{a.description}</div>'

    html = f"""
<div style="font-family:{FONT_STACK_MAP};width:300px;" id="popup_{uid}">
  <!-- Header -->
  <div style="background:{hex_color};color:#fff;padding:12px 16px;border-radius:10px 10px 0 0;">
    <div style="font-size:9px;text-transform:uppercase;letter-spacing:1px;opacity:.85;">{category_label(a.category)}</div>
    <div style="font-size:16px;font-weight:700;margin-top:2px;">{a.name}</div>
  </div>

  <!-- Body -->
  <div style="padding:12px 16px;background:#fff;color:#333;font-size:12px;border-radius:0 0 10px 10px;">
    {desc_html}

    <!-- Meta row: duration, price, score -->
    <div style="display:flex;align-items:center;gap:12px;padding:8px 0;border-top:1px solid #f0f0f0;border-bottom:1px solid #f0f0f0;margin-bottom:8px;">
      <div style="display:flex;align-items:center;gap:4px;" title="Duration">
        <span style="font-size:13px;">\U0001F552</span>
        <span style="font-weight:600;color:#333;" id="dur_display_{uid}">{dur or '—'}</span>
      </div>
      <div style="display:flex;align-items:center;gap:4px;" title="Price">
        <span style="font-size:13px;">\U0001F4B0</span>
        <span style="font-weight:600;color:#333;" id="price_display_{uid}">{price_text or '—'}</span>
      </div>
      <div style="display:flex;align-items:center;gap:4px;" title="Expected score">
        <span style="font-size:13px;">&#x2605;</span>
        <span style="font-weight:600;color:#333;">{score_text or '—'}</span>
      </div>
    </div>

    <!-- User rating (display only) -->
    <div x-show="true" style="margin-bottom:8px;">
      <div style="font-size:10px;color:#999;text-transform:uppercase;letter-spacing:.5px;margin-bottom:3px;">Your rating</div>
      <div style="display:flex;align-items:center;gap:1px;">
        {stars_html}
        <span style="margin-left:6px;font-size:12px;font-weight:600;color:#f39c12;">{f'{user_score:.0f}/10' if user_score else '—'}</span>
      </div>
    </div>

    {tag_pills}
    {tips_html}

    <!-- Action row -->
    <div style="display:flex;gap:6px;margin-top:8px;align-items:center;">
      {url_html}
    </div>
  </div>
</div>
"""
    return html


def _tooltip_html(a: Attraction) -> str:
    """Build a short hover tooltip for an attraction."""
    info = get_category_info(a.category)
    hex_color = info.color
    desc_line = ""
    if a.description:
        short = a.description[:80] + ("..." if len(a.description) > 80 else "")
        desc_line = f'<div style="color:#555;font-size:10px;margin-top:2px;">{short}</div>'
    meta_parts = []
    if a.duration_minutes:
        h, m = divmod(a.duration_minutes, 60)
        meta_parts.append(f"{h}h{m:02d}" if h else f"{m}min")
    if a.price_eur is not None:
        meta_parts.append("Free" if a.price_eur == 0 else f"\u20AC{a.price_eur:.0f}")
    if a.expected_score is not None:
        meta_parts.append(f"\u2605{a.expected_score:.1f}")
    meta_line = ""
    if meta_parts:
        sep = " \u00b7 "
        meta_line = f'<div style="color:#888;font-size:10px;margin-top:1px;">{sep.join(meta_parts)}</div>'
    return (
        f'<div style="font-family:\'{FONT_STACK_MAP}\';font-size:11px;line-height:1.4;max-width:220px;">'
        f'<b>{a.name}</b><br>'
        f'<span style="color:{hex_color};font-weight:600;font-size:10px;">{category_label(a.category)}</span>'
        f'{desc_line}{meta_line}'
        f'</div>'
    )


def _marker_html(emoji: str, name: str) -> str:
    """Emoji icon with name label below — single DivIcon, no overlap."""
    return (
        f'<div style="display:flex;flex-direction:column;align-items:center;pointer-events:auto;">'
        f'<div style="font-size:22px;line-height:1;'
        f'filter:drop-shadow(0 1px 2px rgba(0,0,0,0.3));">{emoji}</div>'
        f'<div class="marker-label" style="font-family:\'{FONT_STACK_MAP}\';font-size:9px;font-weight:600;'
        f'color:#222;text-align:center;max-width:80px;overflow:hidden;text-overflow:ellipsis;'
        f'white-space:nowrap;line-height:1.1;margin-top:1px;'
        f'text-shadow:0 0 3px #fff,0 0 3px #fff,1px 1px 2px #fff,-1px -1px 2px #fff;'
        f'">{name}</div>'
        f'</div>'
    )


class _ControlStyle(MacroElement):
    """DEPRECATED — CSS is now injected directly via folium.Element.

    Kept as empty class to avoid import errors if referenced elsewhere.
    """

    _template = Template("")


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

    # One MarkerCluster per category — each has a name for the layer control
    cluster_opts = {
        "maxClusterRadius": 40,
        "spiderfyOnMaxZoom": True,
        "disableClusteringAtZoom": 15,
        "showCoverageOnHover": False,
    }

    groups: dict[Category, MarkerCluster] = {}
    for cat in Category:
        info = get_category_info(cat)
        groups[cat] = MarkerCluster(
            name=f"{info.html_icon} {info.label}",
            options=cluster_opts,
        )

    for attraction in trip.attractions:
        info = get_category_info(attraction.category)

        popup_html = _popup_html(attraction)
        tooltip_html = _tooltip_html(attraction)

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

    # Add ALL clusters to map (even empty ones show in layer control)
    for cat, cluster in groups.items():
        cluster.add_to(m)

    # Unified layer control (top-right)
    folium.LayerControl(collapsed=False, position='topright').add_to(m)

    # Custom CSS — inject into HTML body (header MacroElement doesn't render reliably)
    css_html = """
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
    .leaflet-control-layers-overlays label span { font-size: 13px; }
    .leaflet-control-layers-separator {
        border-top: 1px solid #e0e0e0 !important;
        margin: 6px 0 !important;
    }
    .leaflet-control-layers-toggle {
        width: 36px !important;
        height: 36px !important;
    }
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
    .marker-cluster-small,
    .marker-cluster-medium,
    .marker-cluster-large {
        background: rgba(255,255,255,0.85) !important;
    }
    .leaflet-popup-content-wrapper {
        padding: 0 !important;
        border-radius: 12px !important;
        overflow: hidden;
        box-shadow: 0 4px 20px rgba(0,0,0,.2) !important;
    }
    .leaflet-popup-content {
        margin: 0 !important;
        width: auto !important;
    }
    .leaflet-popup-close-button {
        z-index: 10 !important;
        color: #fff !important;
        font-size: 20px !important;
        font-weight: 400 !important;
        width: 28px !important;
        height: 28px !important;
        line-height: 28px !important;
        text-align: center;
        right: 6px !important;
        top: 6px !important;
        opacity: 0.8;
        text-shadow: 0 1px 3px rgba(0,0,0,.3);
    }
    .leaflet-popup-close-button:hover {
        color: #fff !important;
        opacity: 1;
    }
    .labels-hidden .marker-label {
        display: none !important;
    }
    .label-toggle-control {
        background: rgba(255,255,255,.95);
        backdrop-filter: blur(4px);
        border-radius: 8px;
        padding: 6px 12px;
        box-shadow: 0 2px 8px rgba(0,0,0,.15);
        font-family: 'Segoe UI', Roboto, Arial, sans-serif;
        font-size: 12px;
        cursor: pointer;
        display: flex;
        align-items: center;
        gap: 6px;
    }
    .label-toggle-control input { cursor: pointer; }
    </style>
    """
    m.get_root().html.add_child(folium.Element(css_html))

    # Label toggle control — inject as raw script referencing the map variable
    map_name = m.get_name()
    label_toggle_js = f"""
    <script>
    (function() {{
        var LabelToggle = L.Control.extend({{
            options: {{ position: 'topright' }},
            onAdd: function(map) {{
                var div = L.DomUtil.create('div', 'label-toggle-control');
                var cb = L.DomUtil.create('input', '', div);
                cb.type = 'checkbox'; cb.checked = true; cb.id = 'label-toggle-cb';
                var lbl = L.DomUtil.create('label', '', div);
                lbl.htmlFor = 'label-toggle-cb';
                lbl.textContent = 'Labels';
                lbl.style.cursor = 'pointer'; lbl.style.margin = '0';
                L.DomEvent.disableClickPropagation(div);
                cb.addEventListener('change', function() {{
                    var c = map.getContainer();
                    if (cb.checked) {{ c.classList.remove('labels-hidden'); }}
                    else {{ c.classList.add('labels-hidden'); }}
                }});
                return div;
            }}
        }});
        new LabelToggle().addTo({map_name});
    }})();
    </script>
    """
    m.get_root().html.add_child(folium.Element(label_toggle_js))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    m.save(str(output_path))
    return output_path
