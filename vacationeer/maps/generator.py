from __future__ import annotations

import statistics
from pathlib import Path

import folium
from branca.element import MacroElement
from folium.plugins import MarkerCluster
from jinja2 import Template

from vacationeer.models.trip import Attraction, Category, Grouping, Trip
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


def _convex_hull(points: list[tuple[float, float]]) -> list[tuple[float, float]]:
    """Compute convex hull using the gift-wrapping (Jarvis march) algorithm."""
    pts = sorted(set(points))
    if len(pts) <= 2:
        return pts

    def cross(o: tuple[float, float], a: tuple[float, float], b: tuple[float, float]) -> float:
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])

    # Build lower hull
    lower: list[tuple[float, float]] = []
    for p in pts:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], p) <= 0:
            lower.pop()
        lower.append(p)
    # Build upper hull
    upper: list[tuple[float, float]] = []
    for p in reversed(pts):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], p) <= 0:
            upper.pop()
        upper.append(p)
    # Concatenate, removing last point of each half (it's repeated)
    return lower[:-1] + upper[:-1]


def _collect_grouping_member_ids(grouping: Grouping, all_groupings: list[Grouping]) -> set[str]:
    """Recursively collect member_ids from a grouping and all its descendants."""
    ids = set(grouping.member_ids)
    children = [g for g in all_groupings if g.parent_id == grouping.id]
    for child in children:
        ids |= _collect_grouping_member_ids(child, all_groupings)
    return ids


class _ControlStyle(MacroElement):
    """DEPRECATED — CSS is now injected directly via folium.Element.

    Kept as empty class to avoid import errors if referenced elsewhere.
    """

    _template = Template("")


def generate_map(trip: Trip, output_path: Path) -> Path:
    if not trip.attractions and not trip.day_trips:
        raise ValueError("Trip has no attractions to map")

    # Gather all locations for center calculation (attractions + day trip subs)
    all_locs = list(trip.attractions)
    for dt in trip.day_trips:
        all_locs.extend(dt.sub_attractions)

    # Filter out coordinate outliers (e.g. 0,0) before computing center
    valid = [a for a in all_locs if not (abs(a.location.lat) < 0.01 and abs(a.location.lng) < 0.01)]
    if not valid:
        valid = all_locs

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

    # Add standalone attractions to category clusters
    for attraction in trip.attractions:
        info = get_category_info(attraction.category)
        marker = folium.Marker(
            location=[attraction.location.lat, attraction.location.lng],
            icon=folium.DivIcon(
                html=_marker_html(info.emoji, attraction.name),
                icon_size=(80, 40),
                icon_anchor=(40, 14),
            ),
            tooltip=folium.Tooltip(_tooltip_html(attraction), sticky=False),
            popup=folium.Popup(_popup_html(attraction), max_width=320),
        )
        marker.add_to(groups[attraction.category])

    # Day trips: each gets its own FeatureGroup for independent toggling
    dt_fgs: list[tuple] = []  # (day_trip, FeatureGroup) pairs
    dt_info = get_category_info(Category.DAY_TRIP)
    for dt in trip.day_trips:
        fg = folium.FeatureGroup(name=dt.name, show=True)
        # Day trip destination marker
        if dt.location and not (abs(dt.location.lat) < 0.01 and abs(dt.location.lng) < 0.01):
            dt_as_attr = Attraction(
                id=dt.id,
                name=dt.name,
                description=dt.description,
                location=dt.location,
                category=Category.DAY_TRIP,
                price_eur=dt.total_price_eur,
                duration_minutes=dt.total_duration_minutes,
                tags=dt.tags,
                tips=dt.tips,
                expected_score=dt.expected_score,
                user_score=dt.user_score,
            )
            folium.Marker(
                location=[dt.location.lat, dt.location.lng],
                icon=folium.DivIcon(
                    html=_marker_html(dt_info.emoji, dt.name),
                    icon_size=(80, 40),
                    icon_anchor=(40, 14),
                ),
                tooltip=folium.Tooltip(_tooltip_html(dt_as_attr), sticky=False),
                popup=folium.Popup(_popup_html(dt_as_attr), max_width=320),
            ).add_to(fg)
        # Sub-attraction markers
        for sub in dt.sub_attractions:
            sub_info = get_category_info(sub.category)
            folium.Marker(
                location=[sub.location.lat, sub.location.lng],
                icon=folium.DivIcon(
                    html=_marker_html(sub_info.emoji, sub.name),
                    icon_size=(80, 40),
                    icon_anchor=(40, 14),
                ),
                tooltip=folium.Tooltip(_tooltip_html(sub), sticky=False),
                popup=folium.Popup(_popup_html(sub), max_width=320),
            ).add_to(fg)
        fg.add_to(m)
        dt_fgs.append((dt, fg))

    # Build attr_by_id from all attractions (standalone + day trip subs)
    all_attractions: list[Attraction] = list(trip.attractions)
    for dt in trip.day_trips:
        all_attractions.extend(dt.sub_attractions)
        if dt.location and not (abs(dt.location.lat) < 0.01 and abs(dt.location.lng) < 0.01):
            all_attractions.append(Attraction(
                id=dt.id, name=dt.name, location=dt.location,
                category=Category.DAY_TRIP,
            ))

    # Grouping polygon overlays (rendered behind markers)
    grouping_fgs: list[tuple] = []  # (grouping, FeatureGroup) pairs for custom control
    attr_by_id: dict[str, Attraction] = {a.id: a for a in all_attractions}
    for grouping in trip.groupings:
        member_ids = _collect_grouping_member_ids(grouping, trip.groupings)
        coords = [
            (attr_by_id[mid].location.lat, attr_by_id[mid].location.lng)
            for mid in member_ids
            if mid in attr_by_id
        ]
        if not coords:
            continue

        fg = folium.FeatureGroup(name=f"\u25CF {grouping.name}", show=False)

        if len(coords) >= 3:
            hull = _convex_hull(coords)
            folium.Polygon(
                locations=hull,
                color=grouping.color,
                fill=True,
                fill_color=grouping.color,
                fill_opacity=0.15,
                weight=2,
                opacity=0.6,
                tooltip=grouping.name,
            ).add_to(fg)
        elif len(coords) == 2:
            folium.PolyLine(
                locations=coords,
                color=grouping.color,
                weight=3,
                opacity=0.5,
                dash_array='10 5',
                tooltip=grouping.name,
            ).add_to(fg)
        else:
            folium.CircleMarker(
                location=coords[0],
                radius=30,
                color=grouping.color,
                fill=True,
                fill_color=grouping.color,
                fill_opacity=0.15,
                tooltip=grouping.name,
            ).add_to(fg)

        fg.add_to(m)
        grouping_fgs.append((grouping, fg))

    # Add ALL clusters to map (even empty ones show in layer control)
    for cat, cluster in groups.items():
        cluster.add_to(m)

    # No Folium LayerControl — we inject a custom one via JS (see below)

    # Custom CSS
    css_html = """
    <style>
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
    .leaflet-popup-close-button:hover { color: #fff !important; opacity: 1; }
    .labels-hidden .marker-label { display: none !important; }
    .vac-layer-ctrl {
        background: rgba(255,255,255,.95);
        backdrop-filter: blur(4px);
        border-radius: 12px;
        padding: 12px 16px;
        box-shadow: 0 2px 12px rgba(0,0,0,.2);
        font-family: 'Segoe UI', Roboto, Arial, sans-serif;
        font-size: 13px;
        min-width: 180px;
        max-height: 70vh;
        overflow-y: auto;
    }
    .vac-layer-ctrl .section-hdr {
        display: flex; align-items: center; justify-content: space-between;
        font-weight: 700; font-size: 11px; text-transform: uppercase;
        color: #666; letter-spacing: .5px; padding: 6px 0 4px; margin-top: 4px;
        border-bottom: 1px solid #e0e0e0;
    }
    .vac-layer-ctrl .section-hdr:first-child { margin-top: 0; }
    .vac-layer-ctrl .section-hdr .toggle-btns { font-weight: 400; text-transform: none; font-size: 11px; }
    .vac-layer-ctrl .toggle-btns a { cursor: pointer; color: #4ea4f6; text-decoration: none; margin-left: 4px; }
    .vac-layer-ctrl .toggle-btns a:hover { text-decoration: underline; }
    .vac-layer-ctrl label {
        display: flex; align-items: center; gap: 6px;
        padding: 3px 0; margin: 0; cursor: pointer; font-size: 13px;
    }
    .vac-layer-ctrl label input { cursor: pointer; margin: 0; }
    .vac-layer-ctrl .g-dot {
        display: inline-block; width: 10px; height: 10px; border-radius: 50%; flex-shrink: 0;
    }
    </style>
    """
    m.get_root().html.add_child(folium.Element(css_html))

    # Build custom layer control — inject as MacroElement so it renders
    # in the script section AFTER Folium's own map/layer initialization.
    # Exclude DAY_TRIP from categories (they have their own section)
    cat_layers_items = [
        {"var": groups[cat].get_name(),
         "label": f"{get_category_info(cat).emoji} {get_category_info(cat).label}",
         "on": True}
        for cat in Category
        if cat != Category.DAY_TRIP
    ]
    dt_layers_items = [
        {"var": fg.get_name(),
         "label": f"{dt_info.emoji} {dt.name}",
         "on": True}
        for dt, fg in dt_fgs
    ]
    grp_layers_items = [
        {"var": fg.get_name(),
         "label": grouping.name,
         "color": grouping.color,
         "on": False}
        for grouping, fg in grouping_fgs
    ]

    class _LayerControl(MacroElement):
        _template = Template("""
            {% macro script(this, kwargs) %}
            (function() {
                var map = {{ this._parent.get_name() }};
                var catLayers = [
                    {% for c in this.cat_items %}
                    {v:{{ c.var }},label:"{{ c.label }}",on:{{ c.on | tojson }}}{{ "," if not loop.last }}
                    {% endfor %}
                ];
                var dtLayers = [
                    {% for d in this.dt_items %}
                    {v:{{ d.var }},label:"{{ d.label }}",on:{{ d.on | tojson }}}{{ "," if not loop.last }}
                    {% endfor %}
                ];
                var grpLayers = [
                    {% for g in this.grp_items %}
                    {v:{{ g.var }},label:"{{ g.label }}",color:"{{ g.color }}",on:{{ g.on | tojson }}}{{ "," if not loop.last }}
                    {% endfor %}
                ];

                var LayerPanel = L.Control.extend({
                    options: { position: 'topright' },
                    onAdd: function() {
                        var div = L.DomUtil.create('div', 'vac-layer-ctrl');
                        L.DomEvent.disableClickPropagation(div);
                        L.DomEvent.disableScrollPropagation(div);

                        function makeSection(title, layers, useColor) {
                            var hdr = document.createElement('div');
                            hdr.className = 'section-hdr';
                            hdr.innerHTML = '<span>' + title + '</span>' +
                                '<span class="toggle-btns"><a class="sel-all">all</a> / <a class="sel-none">none</a></span>';
                            div.appendChild(hdr);

                            var cbs = [];
                            layers.forEach(function(lyr) {
                                var lbl = document.createElement('label');
                                var cb = document.createElement('input');
                                cb.type = 'checkbox'; cb.checked = lyr.on;
                                cb.addEventListener('change', function() {
                                    if (cb.checked) map.addLayer(lyr.v); else map.removeLayer(lyr.v);
                                });
                                lbl.appendChild(cb);
                                if (useColor && lyr.color) {
                                    var dot = document.createElement('span');
                                    dot.className = 'g-dot';
                                    dot.style.background = lyr.color;
                                    lbl.appendChild(dot);
                                }
                                var txt = document.createElement('span');
                                txt.innerHTML = lyr.label;
                                lbl.appendChild(txt);
                                div.appendChild(lbl);
                                cbs.push(cb);
                            });

                            hdr.querySelector('.sel-all').addEventListener('click', function() {
                                cbs.forEach(function(cb, i) { cb.checked = true; map.addLayer(layers[i].v); });
                            });
                            hdr.querySelector('.sel-none').addEventListener('click', function() {
                                cbs.forEach(function(cb, i) { cb.checked = false; map.removeLayer(layers[i].v); });
                            });
                        }

                        makeSection('Categories', catLayers, false);
                        if (dtLayers.length) makeSection('Day Trips', dtLayers, false);
                        if (grpLayers.length) makeSection('Groupings', grpLayers, true);

                        // Labels toggle
                        var sep = document.createElement('div');
                        sep.style.cssText = 'border-top:1px solid #e0e0e0;margin:8px 0 4px';
                        div.appendChild(sep);
                        var lbl = document.createElement('label');
                        var cb = document.createElement('input');
                        cb.type = 'checkbox'; cb.checked = true;
                        cb.addEventListener('change', function() {
                            var c = map.getContainer();
                            if (cb.checked) c.classList.remove('labels-hidden');
                            else c.classList.add('labels-hidden');
                        });
                        lbl.appendChild(cb);
                        var s = document.createElement('span'); s.textContent = 'Labels';
                        lbl.appendChild(s);
                        div.appendChild(lbl);

                        return div;
                    }
                });
                new LayerPanel().addTo(map);
            })();
            {% endmacro %}
        """)

        def __init__(self, cat_items, dt_items, grp_items):
            super().__init__()
            self.cat_items = cat_items
            self.dt_items = dt_items
            self.grp_items = grp_items

    _LayerControl(cat_layers_items, dt_layers_items, grp_layers_items).add_to(m)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    m.save(str(output_path))
    return output_path
