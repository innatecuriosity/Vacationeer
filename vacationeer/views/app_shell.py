from __future__ import annotations

import json
from datetime import date, time
from pathlib import Path

from vacationeer.models.trip import Category, Trip
from vacationeer.theme import CATEGORY_META, GROUPING_PALETTE, PRIMARY
from vacationeer.views.helpers import esc


def _location_picker_xdata() -> str:
    """Return Alpine.js x-data properties for the 3-mode location picker.

    The calling modal's x-data must include form.lat, form.lng, form.address.
    Merge this into the x-data object alongside the modal's own properties.
    """
    # NOTE: This is a plain string, NOT an f-string. Use single braces for JS.
    # When inserted into the caller's f-string via {_location_picker_xdata()},
    # the content is substituted as-is — no brace processing occurs.
    return (
                "\n                locMode: 'gps',"
                "\n                pickerMap: null,"
                "\n                pickerMarker: null,"
                "\n                initPickerMap() {"
                "\n                    var self = this;"
                "\n                    setTimeout(function() {"
                "\n                        if (self.pickerMap) { self.pickerMap.invalidateSize(); return; }"
                "\n                        var el = self.$refs.pickerMapEl;"
                "\n                        if (!el) return;"
                "\n                        self.pickerMap = L.map(el).setView([39.4699, -0.3763], 13);"
                "\n                        L.tileLayer('https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png', {"
                "\n                            attribution: '&copy; OpenStreetMap &copy; CARTO',"
                "\n                            subdomains: 'abcd',"
                "\n                            maxZoom: 20"
                "\n                        }).addTo(self.pickerMap);"
                "\n                        self.pickerMap.on('click', function(e) {"
                "\n                            self.form.lat = e.latlng.lat.toFixed(6);"
                "\n                            self.form.lng = e.latlng.lng.toFixed(6);"
                "\n                            if (self.pickerMarker) self.pickerMap.removeLayer(self.pickerMarker);"
                "\n                            self.pickerMarker = L.marker(e.latlng).addTo(self.pickerMap);"
                "\n                        });"
                "\n                    }, 200);"
                "\n                },"
    )


def _location_picker_html(required: bool = True) -> str:
    """Return the HTML for the 3-mode location picker (Address / GPS / Pick on Map).

    Expects the Alpine scope to have locMode, pickerMap, pickerMarker, initPickerMap()
    from _location_picker_xdata(), and form.lat, form.lng, form.address.
    """
    req = ' <span class="req">*</span>' if required else ""
    return f"""
                    <div class="form-group">
                        <label>Location{req}</label>
                        <div class="loc-tabs">
                            <button type="button" class="loc-tab" :class="locMode === 'address' && 'active'" @click="locMode = 'address'">Address</button>
                            <button type="button" class="loc-tab" :class="locMode === 'gps' && 'active'" @click="locMode = 'gps'">GPS</button>
                            <button type="button" class="loc-tab" :class="locMode === 'map' && 'active'" @click="locMode = 'map'; initPickerMap()">Pick on Map</button>
                        </div>
                    </div>
                    <div class="form-group" x-show="locMode === 'address'">
                        <input type="text" x-model="form.address" placeholder="Enter full address">
                    </div>
                    <div class="form-row" x-show="locMode === 'gps' || locMode === 'address'">
                        <div class="form-group">
                            <label>Latitude</label>
                            <input type="number" step="any" x-model="form.lat" placeholder="39.4699">
                        </div>
                        <div class="form-group">
                            <label>Longitude</label>
                            <input type="number" step="any" x-model="form.lng" placeholder="-0.3763">
                        </div>
                    </div>
                    <div x-show="locMode === 'map'">
                        <div class="loc-map-container" x-ref="pickerMapEl"></div>
                        <div class="form-row">
                            <div class="form-group">
                                <label>Lat</label>
                                <input type="number" step="any" x-model="form.lat" readonly style="background:#f5f6f8;">
                            </div>
                            <div class="form-group">
                                <label>Lng</label>
                                <input type="number" step="any" x-model="form.lng" readonly style="background:#f5f6f8;">
                            </div>
                        </div>
                    </div>"""


def _json_serializer(obj: object) -> str:
    """Handle date/time serialization for JSON."""
    if isinstance(obj, date):
        return obj.isoformat()
    if isinstance(obj, time):
        return obj.isoformat()
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


def generate_app(
    trip: Trip,
    map_filename: str,
    output_path: Path,
    tab_contents: dict[str, str] | None = None,
) -> Path:
    """Generate the main app HTML file.

    Args:
        trip: Trip model instance
        map_filename: filename of the map HTML (same directory)
        output_path: Path to write the HTML to
        tab_contents: Optional dict mapping tab id to HTML content
                     e.g. {"overview-content": "<div>...</div>"}

    Returns:
        The path the HTML was written to.
    """
    tab_contents = tab_contents or {}
    output_path = Path(output_path)

    date_fmt = "%b %d, %Y"
    start = trip.start_date.strftime(date_fmt)
    end = trip.end_date.strftime(date_fmt)
    num_days = (trip.end_date - trip.start_date).days + 1

    overview_inner = tab_contents.get("overview-content", "")
    timeline_inner = tab_contents.get("timeline-content", "")
    grouping_palette = GROUPING_PALETTE

    trip_json = json.dumps(
        trip.model_dump(mode="json"),
        default=_json_serializer,
        ensure_ascii=False,
    )

    category_options = "\n".join(
        f'                        <option value="{c.value}">{info.label}</option>'
        for c, info in CATEGORY_META.items()
    )

    pace_options = "\n".join(
        f'                            <option value="{p}">{p.title()}</option>'
        for p in ("relaxed", "moderate", "fast")
    )

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{esc(trip.name)} - Vacationeer</title>
<meta name="theme-color" content="#1a2332">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<link rel="manifest" href="manifest.json">
<link rel="icon" type="image/svg+xml" href="icon.svg">
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<script src="https://cdn.jsdelivr.net/npm/sortablejs@1.15.6/Sortable.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
<script defer src="https://cdn.jsdelivr.net/npm/alpinejs@3.x.x/dist/cdn.min.js"></script>
<style>
*, *::before, *::after {{
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}}
[x-cloak] {{ display: none !important; }}
html, body {{
    height: 100%;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    color: #1a2332;
    background: #fff;
}}

/* ---- layout ---- */
.app {{
    display: flex;
    height: 100vh;
    overflow: hidden;
}}

/* ---- sidebar ---- */
.sidebar {{
    width: 340px;
    min-width: 340px;
    background: #1a2332;
    color: #fff;
    display: flex;
    flex-direction: column;
    transition: width 0.25s ease, min-width 0.25s ease;
    overflow: hidden;
}}
.sidebar-header {{
    padding: 20px 18px 16px;
    border-bottom: 1px solid rgba(255,255,255,0.08);
}}
.sidebar-header .brand {{
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 1.5px;
    opacity: 0.5;
    margin-bottom: 6px;
    white-space: nowrap;
}}
.sidebar-header .trip-name {{
    font-size: 16px;
    font-weight: 600;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}}

/* ---- trip picker ---- */
.trip-picker {{
    position: relative;
}}
.trip-picker-btn {{
    display: flex;
    align-items: center;
    gap: 6px;
    width: 100%;
    background: rgba(255,255,255,0.08);
    border: 1px solid rgba(255,255,255,0.12);
    border-radius: 6px;
    padding: 8px 10px;
    color: #fff;
    font-size: 14px;
    font-weight: 600;
    font-family: inherit;
    cursor: pointer;
    text-align: left;
    transition: background 0.15s;
    margin-top: 6px;
}}
.trip-picker-btn:hover {{
    background: rgba(255,255,255,0.14);
}}
.trip-picker-btn .tp-label {{
    flex: 1;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}}
.trip-picker-btn .tp-chevron {{
    font-size: 10px;
    opacity: 0.5;
    transition: transform 0.2s;
}}
.trip-picker-btn .tp-chevron.open {{
    transform: rotate(180deg);
}}
.tp-dropdown {{
    display: none;
    position: absolute;
    top: calc(100% + 4px);
    left: 0;
    right: 0;
    background: #243040;
    border: 1px solid rgba(255,255,255,0.12);
    border-radius: 8px;
    box-shadow: 0 8px 24px rgba(0,0,0,0.4);
    z-index: 100;
    max-height: 300px;
    overflow-y: auto;
}}
.tp-dropdown.open {{
    display: block;
}}
.tp-dropdown .tp-item {{
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 10px 12px;
    color: rgba(255,255,255,0.8);
    font-size: 13px;
    cursor: pointer;
    transition: background 0.12s;
    border: none;
    background: none;
    width: 100%;
    text-align: left;
    font-family: inherit;
}}
.tp-dropdown .tp-item:hover {{
    background: rgba(255,255,255,0.1);
    color: #fff;
}}
.tp-dropdown .tp-item.active {{
    color: #4ea4f6;
    font-weight: 600;
}}
.tp-dropdown .tp-item .tp-status {{
    font-size: 10px;
    opacity: 0.5;
    margin-left: auto;
}}
.tp-dropdown .tp-item .tp-status.tp-loading {{
    opacity: 1;
    color: #4ea4f6;
    animation: tp-pulse 1.5s ease-in-out infinite;
}}
@keyframes tp-pulse {{
    0%, 100% {{ opacity: 1; }}
    50% {{ opacity: 0.4; }}
}}
.tp-dropdown .tp-divider {{
    border-top: 1px solid rgba(255,255,255,0.08);
    margin: 4px 0;
}}
.tp-dropdown .tp-new {{
    color: #4ea4f6;
    font-weight: 500;
}}

.nav {{
    list-style: none;
    padding: 12px 0;
    flex-shrink: 0;
}}
.nav li {{
    position: relative;
}}
.nav-btn {{
    display: flex;
    align-items: center;
    gap: 12px;
    width: 100%;
    padding: 12px 20px;
    background: none;
    border: none;
    color: rgba(255,255,255,0.7);
    font-size: 14px;
    font-family: inherit;
    cursor: pointer;
    text-align: left;
    transition: background 0.15s, color 0.15s;
    white-space: nowrap;
}}
.nav-btn:hover {{
    background: rgba(255,255,255,0.1);
    color: #fff;
}}
.nav-btn.active {{
    color: #fff;
    background: rgba(255,255,255,0.1);
    border-left: 3px solid #4ea4f6;
    padding-left: 17px;
}}
.nav-btn .icon {{
    font-size: 18px;
    width: 24px;
    text-align: center;
    flex-shrink: 0;
}}
.nav-btn .label {{
    overflow: hidden;
    text-overflow: ellipsis;
}}

.sidebar-footer {{
    padding: 14px 18px;
    border-top: 1px solid rgba(255,255,255,0.08);
    font-size: 12px;
    opacity: 0.35;
    white-space: nowrap;
}}

/* ---- main ---- */
.main {{
    flex: 1;
    display: flex;
    flex-direction: column;
    overflow: hidden;
    background: #fff;
}}

.header {{
    padding: 18px 28px;
    border-bottom: 1px solid #e8eaed;
    background: #fff;
}}
.header-title-row {{
    display: flex;
    align-items: center;
    gap: 8px;
    cursor: pointer;
    margin-bottom: 4px;
}}
.header-title-row:hover .edit-icon {{
    opacity: 1;
}}
.header h1 {{
    font-size: 20px;
    font-weight: 700;
    color: #1a2332;
    margin: 0;
}}
.edit-icon {{
    font-size: 14px;
    opacity: 0.3;
    transition: opacity 0.2s;
}}
.header .meta {{
    font-size: 13px;
    color: #5f6b7a;
    display: flex;
    gap: 18px;
    flex-wrap: wrap;
}}
.header .meta span {{
    display: inline-flex;
    align-items: center;
    gap: 5px;
}}

.content {{
    flex: 1;
    overflow: auto;
    background: #f5f6f8;
}}

.tab-panel {{
    display: none;
    height: 100%;
}}
.tab-panel.active {{
    display: block;
}}

#tab-map {{
    padding: 0;
}}
#tab-map iframe {{
    width: 100%;
    height: 100%;
    border: none;
}}

#tab-overview, #tab-timeline {{
    padding: 24px 28px;
}}
.tab-placeholder {{
    color: #8893a2;
    font-size: 14px;
    padding: 40px 0;
    text-align: center;
}}

/* ---- modal ---- */
.modal-backdrop {{
    position: fixed;
    inset: 0;
    background: rgba(0,0,0,0.5);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 1000;
}}
.modal {{
    background: #fff;
    border-radius: 12px;
    max-width: 600px;
    width: 90%;
    max-height: 85vh;
    overflow-y: auto;
    box-shadow: 0 20px 60px rgba(0,0,0,0.3);
}}
.modal-header {{
    background: #1a2332;
    color: #fff;
    padding: 18px 24px;
    border-radius: 12px 12px 0 0;
    font-size: 16px;
    font-weight: 600;
}}
.modal-body {{
    padding: 24px;
}}
.form-group {{
    margin-bottom: 16px;
}}
.form-group label {{
    display: block;
    font-size: 13px;
    font-weight: 600;
    color: #374151;
    margin-bottom: 4px;
}}
.form-group input,
.form-group textarea,
.form-group select {{
    width: 100%;
    padding: 8px 12px;
    border: 1px solid #d1d5db;
    border-radius: 6px;
    font-size: 14px;
    font-family: inherit;
    color: #1a2332;
    transition: border-color 0.15s;
}}
.form-group input:focus,
.form-group textarea:focus,
.form-group select:focus {{
    outline: none;
    border-color: #4ea4f6;
    box-shadow: 0 0 0 2px rgba(78,164,246,0.15);
}}
.form-group textarea {{
    resize: vertical;
    min-height: 60px;
}}
.form-row {{
    display: flex;
    gap: 12px;
}}
.form-row .form-group {{
    flex: 1;
}}
.modal-actions {{
    display: flex;
    justify-content: flex-end;
    gap: 10px;
    padding-top: 8px;
}}
.btn {{
    padding: 9px 20px;
    border: none;
    border-radius: 6px;
    font-size: 14px;
    font-family: inherit;
    font-weight: 500;
    cursor: pointer;
    transition: background 0.15s;
}}
.btn-primary {{
    background: #1a2332;
    color: #fff;
}}
.btn-primary:hover {{
    background: #2a3a4e;
}}
.btn-cancel {{
    background: #e5e7eb;
    color: #374151;
}}
.btn-cancel:hover {{
    background: #d1d5db;
}}

/* ---- required field marker ---- */
label .req {{ color: #e74c3c; font-weight: bold; }}
.form-hint {{ font-size: 12px; color: #999; margin-top: 8px; }}

/* ---- fab ---- */
.fab-container {{ position: fixed; bottom: 30px; right: 30px; z-index: 1000; }}
.fab {{
    width: 56px;
    height: 56px;
    border-radius: 50%;
    background: #1a2332;
    color: #fff;
    font-size: 28px;
    border: none;
    cursor: pointer;
    box-shadow: 0 4px 16px rgba(0,0,0,0.25);
    display: flex;
    align-items: center;
    justify-content: center;
    transition: background 0.15s, transform 0.15s;
    z-index: 900;
}}
.fab:hover {{
    background: #2a3a4e;
    transform: scale(1.08);
}}
.fab-active {{ transform: rotate(45deg); }}
.fab-menu {{ position: absolute; bottom: 60px; right: 0; background: white; border-radius: 8px; box-shadow: 0 4px 20px rgba(0,0,0,0.15); overflow: hidden; min-width: 160px; }}
.fab-menu button {{ display: flex; align-items: center; gap: 8px; width: 100%; padding: 10px 16px; border: none; background: white; cursor: pointer; font-size: 14px; }}
.fab-menu button:hover {{ background: #f5f6f8; }}

/* ---- toasts ---- */
.toast-container {{
    position: fixed;
    top: 20px;
    right: 20px;
    z-index: 2000;
    display: flex;
    flex-direction: column;
    gap: 8px;
}}
.toast {{
    padding: 12px 20px;
    border-radius: 8px;
    color: #fff;
    font-size: 14px;
    font-weight: 500;
    box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    animation: toast-in 0.3s ease;
}}
.toast.success {{
    background: #059669;
}}
.toast.error {{
    background: #dc2626;
}}
.toast.info {{
    background: #2563eb;
}}
@keyframes toast-in {{
    from {{ opacity: 0; transform: translateX(40px); }}
    to {{ opacity: 1; transform: translateX(0); }}
}}

/* ---- sidebar chat ---- */
.sidebar-chat {{
    flex: 1;
    display: flex;
    flex-direction: column;
    border-top: 1px solid rgba(255,255,255,0.08);
    min-height: 0;
}}
.sidebar-chat .chat-header {{
    padding: 10px 18px;
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 1.2px;
    opacity: 0.5;
    flex-shrink: 0;
}}
.sidebar-chat .chat-messages {{
    flex: 1;
    overflow-y: auto;
    padding: 8px 14px;
    display: flex;
    flex-direction: column;
    gap: 10px;
    min-height: 0;
}}
.sidebar-chat .chat-messages::-webkit-scrollbar {{
    width: 4px;
}}
.sidebar-chat .chat-messages::-webkit-scrollbar-thumb {{
    background: rgba(255,255,255,0.15);
    border-radius: 2px;
}}
.chat-bubble {{
    max-width: 100%;
    padding: 10px 14px;
    border-radius: 14px;
    font-size: 13px;
    line-height: 1.5;
    word-wrap: break-word;
}}
.chat-bubble.user {{
    white-space: pre-wrap;
    align-self: flex-end;
    background: #4ea4f6;
    color: #fff;
    border-bottom-right-radius: 4px;
}}
.chat-bubble.assistant {{
    align-self: flex-start;
    background: rgba(255,255,255,0.1);
    color: rgba(255,255,255,0.9);
    border-bottom-left-radius: 4px;
}}
.chat-bubble.assistant p {{ margin: 0 0 8px 0; }}
.chat-bubble.assistant p:last-child {{ margin-bottom: 0; }}
.chat-bubble.assistant ul, .chat-bubble.assistant ol {{ margin: 4px 0; padding-left: 20px; }}
.chat-bubble.assistant li {{ margin: 2px 0; }}
.chat-bubble.assistant code {{ background: rgba(255,255,255,0.1); padding: 1px 4px; border-radius: 3px; font-size: 12px; }}
.chat-bubble.assistant strong {{ color: #fff; }}
.chat-bubble.error {{
    align-self: flex-start;
    background: rgba(220,53,69,0.3);
    color: #ffb3b3;
    border-bottom-left-radius: 4px;
    font-size: 12px;
}}
.chat-bubble .typing {{
    display: inline-block;
    animation: pulse-typing 1.2s infinite;
}}
@keyframes pulse-typing {{
    0%, 100% {{ opacity: 0.4; }}
    50% {{ opacity: 1; }}
}}
.sidebar-chat .chat-input {{
    display: flex;
    gap: 6px;
    padding: 10px 14px;
    border-top: 1px solid rgba(255,255,255,0.08);
    flex-shrink: 0;
}}
.sidebar-chat .chat-input input {{
    flex: 1;
    padding: 8px 12px;
    border: 1px solid rgba(255,255,255,0.15);
    border-radius: 18px;
    background: rgba(255,255,255,0.08);
    color: #fff;
    font-size: 13px;
    font-family: inherit;
    outline: none;
}}
.sidebar-chat .chat-input input::placeholder {{
    color: rgba(255,255,255,0.35);
}}
.sidebar-chat .chat-input input:focus {{
    border-color: #4ea4f6;
    background: rgba(255,255,255,0.12);
}}
.sidebar-chat .chat-input button {{
    padding: 8px 14px;
    background: #4ea4f6;
    color: #fff;
    border: none;
    border-radius: 18px;
    font-size: 12px;
    font-weight: 600;
    cursor: pointer;
    font-family: inherit;
    white-space: nowrap;
}}
.sidebar-chat .chat-input button:hover {{
    background: #3b8de0;
}}
.sidebar-chat .chat-input button:disabled {{
    opacity: 0.5;
    cursor: not-allowed;
}}

/* ---- location picker ---- */
.loc-tabs {{ display: flex; gap: 0; margin-bottom: 12px; border-radius: 6px; overflow: hidden; border: 1px solid #d1d5db; }}
.loc-tab {{ flex: 1; padding: 8px; text-align: center; font-size: 12px; font-weight: 600; cursor: pointer; background: #f5f6f8; border: none; color: #5f6b7a; }}
.loc-tab.active {{ background: #1a2332; color: #fff; }}
.loc-map-container {{ width: 100%; height: 250px; border-radius: 8px; border: 2px solid #d1d5db; margin-bottom: 8px; }}

/* ---- responsive ---- */
@media (max-width: 768px) {{
    .sidebar {{
        width: 60px;
        min-width: 60px;
    }}
    .sidebar-header .brand,
    .sidebar-header .trip-name,
    .trip-picker,
    .nav-btn .label,
    .sidebar-footer,
    .sidebar-chat {{
        display: none;
    }}
    .sidebar-header {{
        padding: 16px 0;
        text-align: center;
    }}
    .nav-btn {{
        justify-content: center;
        padding: 14px 0;
    }}
    .nav-btn.active {{
        border-left: 3px solid #4ea4f6;
        padding-left: 0;
    }}
    .header {{
        padding: 14px 16px;
    }}
    .header h1 {{
        font-size: 17px;
    }}
    #tab-overview, #tab-timeline {{
        padding: 16px;
    }}
    .fab {{
        bottom: 20px;
        right: 20px;
        width: 48px;
        height: 48px;
        font-size: 24px;
    }}
}}
</style>
</head>
<body>

<script>
window.__TRIP_DATA__ = {trip_json};
// Restore from localStorage if we have local edits
(function() {{
    var key = 'vacationeer_trip_' + (window.__TRIP_DATA__.id || 'default');
    var saved = localStorage.getItem(key);
    if (saved) {{
        try {{
            var local = JSON.parse(saved);
            // Only use local if it has a _localTs (was saved by offline layer)
            if (local._localTs) {{
                // Merge: keep local mutations over embedded data
                Object.assign(window.__TRIP_DATA__, local);
            }}
        }} catch(e) {{ /* ignore corrupt data */ }}
    }}
}})();
</script>

<script>
// Offline-aware fetch: try server first, fall back to local mutation
async function offlineFetch(url, opts, localFallback) {{
    try {{
        var resp = await fetch(url, opts);
        if (resp.ok) return {{ ok: true, resp: resp }};
        // Server returned error (404 on GitHub Pages, etc.) — fall back to local
        if (localFallback) {{ localFallback(); return {{ ok: true, resp: null, offline: true }}; }}
        return {{ ok: false, resp: resp }};
    }} catch(e) {{
        // Network error — we're offline
        if (localFallback) {{ localFallback(); return {{ ok: true, resp: null, offline: true }}; }}
        return {{ ok: false, resp: null, offline: true }};
    }}
}}

// Helper: try fetch, on ANY failure (network or HTTP error) run local fallback
async function tryServerOrLocal(url, opts, onSuccess, localFallback) {{
    try {{
        var resp = await fetch(url, opts);
        if (resp.ok) {{ await onSuccess(resp); return; }}
        // HTTP error (e.g. 404 on static hosting) — use local fallback
        localFallback();
    }} catch(e) {{
        // Network error — use local fallback
        localFallback();
    }}
}}

function _persistLocal() {{
    var store = Alpine.store('trip');
    var key = 'vacationeer_trip_' + (store.id || 'default');
    var data = {{}};
    // Copy serializable trip fields
    ['id','name','destination','start_date','end_date','travelers','budget_eur',
     'attractions','days','day_trips','preferences','travel_segments'].forEach(function(f) {{
        if (store[f] !== undefined) data[f] = JSON.parse(JSON.stringify(store[f]));
    }});
    data._localTs = Date.now();
    localStorage.setItem(key, JSON.stringify(data));
}}

function _genId() {{
    // crypto.randomUUID available on all modern browsers
    if (crypto.randomUUID) return crypto.randomUUID();
    return 'local-' + Date.now() + '-' + Math.random().toString(36).substr(2, 9);
}}

function reloadMap() {{
    setTimeout(function() {{
        var iframe = document.querySelector('#tab-map iframe');
        if (iframe) iframe.src = iframe.src.split('?')[0] + '?t=' + Date.now();
    }}, 1500);
}}

/* Listen for messages from map iframe (e.g. after inline edit) */
window.addEventListener('message', function(e) {{
    if (e.data && e.data.type === 'attraction-updated') {{
        var store = Alpine.store('trip');
        if (store && store.reload) store.reload();
    }}
}});

/* Trip picker — plain JS, no Alpine for open/close */
(function() {{
    var tripSlug = '{esc(trip.id)}';
    var pipelineInterval = null;

    function initTripPicker() {{
        var btn = document.getElementById('tp-btn');
        var dd = document.getElementById('tp-dropdown');
        var chevron = btn && btn.querySelector('.tp-chevron');
        if (!btn || !dd) return;

        btn.addEventListener('click', function(e) {{
            e.stopPropagation();
            var isOpen = dd.classList.contains('open');
            if (isOpen) {{
                dd.classList.remove('open');
                if (chevron) chevron.classList.remove('open');
            }} else {{
                loadTrips();
                dd.classList.add('open');
                if (chevron) chevron.classList.add('open');
            }}
        }});

        document.addEventListener('click', function(e) {{
            if (!dd.contains(e.target) && e.target !== btn) {{
                dd.classList.remove('open');
                if (chevron) chevron.classList.remove('open');
            }}
        }});

        document.addEventListener('keydown', function(e) {{
            if (e.key === 'Escape') {{
                dd.classList.remove('open');
                if (chevron) chevron.classList.remove('open');
            }}
        }});
    }}

    function loadTrips() {{
        var list = document.getElementById('tp-list');
        if (!list) return;
        fetch('/api/trips').then(function(r) {{
            return r.ok ? r.json() : [];
        }}).then(function(trips) {{
            list.innerHTML = '';
            trips.forEach(function(t) {{
                var b = document.createElement('button');
                b.className = 'tp-item' + (t.active ? ' active' : '');
                var name = document.createElement('span');
                name.textContent = t.name || t.slug;
                b.appendChild(name);
                var status = document.createElement('span');
                status.className = 'tp-status';
                if (t.pipeline && t.pipeline.status !== 'done' && t.pipeline.status !== 'error') {{
                    status.className += ' tp-loading';
                    status.textContent = t.pipeline.step || 'working...';
                }} else {{
                    status.textContent = t.has_trip ? '' : 'config';
                }}
                b.appendChild(status);
                b.addEventListener('click', function() {{
                    document.getElementById('tp-dropdown').classList.remove('open');
                    if (t.active) return;
                    if (t.app_url) window.location.href = t.app_url;
                }});
                list.appendChild(b);
            }});
        }}).catch(function() {{}});
    }}

    // Pipeline progress polling for current trip
    function checkPipeline() {{
        var banner = document.getElementById('pipeline-banner');
        if (!banner) return;
        fetch('/api/pipeline/status/' + tripSlug).then(function(r) {{
            return r.ok ? r.json() : null;
        }}).then(function(d) {{
            if (!d || d.status === 'done' || d.status === 'error') {{
                if (d && d.status === 'done' && banner.style.display !== 'none') {{
                    banner.querySelector('.pp-step').textContent = 'Ready! Reloading...';
                    setTimeout(function() {{ window.location.reload(); }}, 1000);
                }}
                if (pipelineInterval) {{ clearInterval(pipelineInterval); pipelineInterval = null; }}
                if (d && d.status === 'error') {{
                    banner.style.display = 'block';
                    banner.querySelector('.pp-step').textContent = 'Error: ' + (d.error || 'Unknown');
                    banner.querySelector('.pp-bar').style.width = '100%';
                    banner.querySelector('.pp-bar').style.background = '#e74c3c';
                }}
                return;
            }}
            banner.style.display = 'block';
            banner.querySelector('.pp-step').textContent = d.step || 'Working...';
            var pctMap = {{queued:5, researching:25, converting:55, building:80}};
            var pct = pctMap[d.status] || 10;
            banner.querySelector('.pp-bar').style.width = pct + '%';
            if (!pipelineInterval) {{
                pipelineInterval = setInterval(function() {{ checkPipeline(); }}, 3000);
            }}
        }}).catch(function() {{}});
    }}

    document.addEventListener('DOMContentLoaded', function() {{
        initTripPicker();
        checkPipeline();
    }});
}})()

/* New trip form component */
function newTripForm() {{
    return {{
        phase: 'form',
        pollInterval: null,
        form: {{
            destination: '',
            name: '',
            start_date: '',
            end_date: '',
            travelers: 2,
            budget_eur: null,
            interests_str: '',
            pace: 'moderate',
            include_day_trips: 'true',
            must_do: '',
            context: ''
        }},
        job: {{
            slug: '',
            status: 'queued',
            step: '',
            error: null,
            attractions_count: 0,
            day_trips_count: 0,
            app_url: null
        }},
        async submit() {{
            var dest = this.form.destination.trim();
            if (!dest || !this.form.start_date || !this.form.end_date) return;

            var interests = this.form.interests_str
                ? this.form.interests_str.split(',').map(function(s) {{ return s.trim(); }}).filter(Boolean)
                : [];
            var payload = {{
                destination: dest,
                start_date: this.form.start_date,
                end_date: this.form.end_date,
                travelers: parseInt(this.form.travelers) || 2,
                interests: interests,
                pace: this.form.pace,
                include_day_trips: this.form.include_day_trips === 'true'
            }};
            if (this.form.name) payload.name = this.form.name;
            if (this.form.budget_eur) payload.budget_eur = parseFloat(this.form.budget_eur);
            if (this.form.must_do) payload.must_do = this.form.must_do;
            if (this.form.context) payload.context = this.form.context;

            try {{
                var resp = await fetch('/api/pipeline/start', {{
                    method: 'POST',
                    headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify(payload)
                }});
                if (!resp.ok) {{
                    var err = await resp.json().catch(function() {{ return {{detail: 'Failed to start pipeline'}}; }});
                    alert(err.detail || 'Failed to start pipeline');
                    return;
                }}
                var data = await resp.json();
                this.job.slug = data.slug;
                this.job.status = data.status;
                this.job.step = data.step || 'Starting...';
                // Navigate immediately to the new (skeleton) trip page
                var destSlug = dest.split(',')[0].trim().toLowerCase().replace(/[^a-z0-9]+/g, '-');
                var appUrl = '/' + destSlug + '-app.html';
                window.dispatchEvent(new CustomEvent('close-modal'));
                window.location.href = appUrl;
            }} catch (e) {{
                alert('Network error: ' + e.message);
            }}
        }},
        startPolling() {{
            var self = this;
            this.pollInterval = setInterval(async function() {{
                try {{
                    var resp = await fetch('/api/pipeline/status/' + self.job.slug);
                    if (!resp.ok) return;
                    var data = await resp.json();
                    self.job.status = data.status;
                    self.job.step = data.step;
                    self.job.error = data.error;
                    self.job.attractions_count = data.attractions_count || 0;
                    self.job.day_trips_count = data.day_trips_count || 0;
                    if (data.status === 'done') {{
                        self.job.app_url = data.app_url || null;
                        self.stopPolling();
                    }} else if (data.status === 'error') {{
                        self.stopPolling();
                    }}
                }} catch (e) {{
                    /* ignore polling errors */
                }}
            }}, 3000);
        }},
        stopPolling() {{
            if (this.pollInterval) {{
                clearInterval(this.pollInterval);
                this.pollInterval = null;
            }}
        }},
        cleanup() {{
            this.stopPolling();
        }},
        statusIcon() {{
            var s = this.job.status;
            if (s === 'error') return '⚠';
            if (s === 'done') return '✓';
            if (s === 'researching') return '🔍';
            if (s === 'converting') return '⚙';
            if (s === 'building') return '🏗';
            return '⏳';
        }},
        progressPct() {{
            var map = {{ queued: 5, researching: 25, converting: 55, building: 80, done: 100, error: 100 }};
            return map[this.job.status] || 5;
        }},
        progressStepStyle(step) {{
            var order = ['queued', 'researching', 'converting', 'building', 'done'];
            var current = order.indexOf(this.job.status);
            var target = order.indexOf(step);
            if (this.job.status === 'error') return 'color:#dc2626';
            if (target < current) return 'color:#059669;font-weight:600';
            if (target === current) return 'color:#1a2332;font-weight:600';
            return '';
        }}
    }};
}}

/* Sidebar chat component */
function sidebarChat() {{
    var STORAGE_KEY = 'vacationeer_chat';
    var defaultMsg = {{ role: 'assistant', content: "Hi! Type /help for commands, or ask me anything about {esc(trip.destination)}." }};
    var saved = [];
    try {{ saved = JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]'); }} catch(e) {{}}
    if (!saved.length) saved = [defaultMsg];

    return {{
        messages: saved,
        input: '',
        loading: false,
        persist() {{
            try {{ localStorage.setItem(STORAGE_KEY, JSON.stringify(this.messages)); }} catch(e) {{}}
        }},
        scrollToBottom() {{
            var self = this;
            this.$nextTick(function() {{
                var el = self.$refs.chatMessages;
                if (el) el.scrollTop = el.scrollHeight;
            }});
        }},
        clearChat() {{
            this.messages = [defaultMsg];
            this.persist();
        }},
        renderMd(text) {{
            if (typeof marked !== 'undefined' && marked.parse) {{
                return marked.parse(text || '', {{ breaks: true }});
            }}
            return (text || '').replace(/\\n/g, '<br>');
        }},
        init() {{
            this.scrollToBottom();
        }},
        handleSkill(text) {{
            // Return {{handled: true, response: '...'}} or {{handled: false}}
            var parts = text.split(/\s+/);
            var cmd = parts[0].toLowerCase();
            var args = parts.slice(1).join(' ').trim();
            var store = Alpine.store('trip');

            if (cmd === '/help' || cmd === '/?') {{
                return {{handled: true, response:
                    'Available commands:\\n' +
                    '/add <name> - Add attraction (opens add form)\\n' +
                    '/schedule <id> <date> [time] - Schedule attraction to a day\\n' +
                    '/day <date> [label] - Create a new day\\n' +
                    '/list - List all attractions with IDs\\n' +
                    '/unscheduled - Show unscheduled attractions\\n' +
                    '/days - Show scheduled days\\n' +
                    'Or just type a question for the AI assistant.'
                }};
            }}

            if (cmd === '/list') {{
                var attrs = (store.attractions || []);
                if (!attrs.length) return {{handled: true, response: 'No attractions yet.'}};
                var lines = attrs.map(function(a) {{
                    var meta = [];
                    if (a.category) meta.push(a.category);
                    if (a.price_eur != null) meta.push(a.price_eur === 0 ? 'Free' : a.price_eur + ' EUR');
                    if (a.duration_minutes) meta.push(a.duration_minutes + 'min');
                    return a.id + ' - ' + a.name + (meta.length ? ' (' + meta.join(', ') + ')' : '');
                }});
                return {{handled: true, response: 'Attractions (' + attrs.length + '):\\n' + lines.join('\\n')}};
            }}

            if (cmd === '/unscheduled') {{
                var scheduled = {{}};
                (store.days || []).forEach(function(d) {{
                    (d.activities || []).forEach(function(a) {{
                        if (a.attraction_id) scheduled[a.attraction_id] = true;
                    }});
                }});
                var unsch = (store.attractions || []).filter(function(a) {{ return !scheduled[a.id]; }});
                if (!unsch.length) return {{handled: true, response: 'All attractions are scheduled!'}};
                var lines = unsch.map(function(a) {{ return a.id + ' - ' + a.name; }});
                return {{handled: true, response: 'Unscheduled (' + unsch.length + '):\\n' + lines.join('\\n')}};
            }}

            if (cmd === '/days') {{
                var days = (store.days || []);
                if (!days.length) return {{handled: true, response: 'No days created yet. Use /day YYYY-MM-DD to create one.'}};
                var lines = days.map(function(d) {{
                    var acts = (d.activities || []).map(function(a) {{ return (a.start_time || '?') + ' ' + a.name; }});
                    return d.date + (d.label ? ' (' + d.label + ')' : '') + ': ' + (acts.length ? acts.join(', ') : 'empty');
                }});
                return {{handled: true, response: 'Days (' + days.length + '):\\n' + lines.join('\\n')}};
            }}

            if (cmd === '/add') {{
                if (!args) return {{handled: true, response: 'Usage: /add <place name>\\nI will search for info and add it automatically.'}};
                // AI-powered: send to /api/chat/add which researches and returns structured data
                return {{handled: true, asyncAction: 'add', query: args}};
            }}

            if (cmd === '/schedule') {{
                // /schedule attraction-id 2026-03-22 10:00
                var sParts = args.split(/\s+/);
                if (sParts.length < 2) return {{handled: true, response: 'Usage: /schedule <attraction-id> <YYYY-MM-DD> [HH:MM]'}};
                var attrId = sParts[0], date = sParts[1], time = sParts[2] || null;
                return {{handled: true, action: 'schedule', data: {{attraction_id: attrId, date: date, start_time: time}}}};
            }}

            if (cmd === '/day') {{
                if (!args) return {{handled: true, response: 'Usage: /day <YYYY-MM-DD> [label]'}};
                var dParts = args.split(/\s+/);
                var date = dParts[0], label = dParts.slice(1).join(' ') || '';
                return {{handled: true, action: 'add_day', data: {{date: date, label: label}}}};
            }}

            return {{handled: false}};
        }},
        async send() {{
            var text = this.input.trim();
            if (!text || this.loading) return;
            this.messages.push({{ role: 'user', content: text }});
            this.input = '';
            this.persist();
            this.scrollToBottom();

            // Check for /commands first
            if (text.startsWith('/')) {{
                var skill = this.handleSkill(text);
                if (skill.handled) {{
                    if (skill.asyncAction === 'add') {{
                        // AI-powered add: research + add
                        this.messages.push({{ role: 'assistant', content: 'Researching "' + skill.query + '"...' }});
                        this.loading = true;
                        this.persist();
                        this.scrollToBottom();
                        try {{
                            var resp = await fetch('/api/chat/add', {{
                                method: 'POST',
                                headers: {{ 'Content-Type': 'application/json' }},
                                body: JSON.stringify({{ query: skill.query }})
                            }});
                            var data = await resp.json();
                            if (resp.ok && data.attraction) {{
                                await Alpine.store('trip').addAttraction(data.attraction);
                                this.messages.push({{ role: 'assistant', content: 'Added "' + data.attraction.name + '"' + (data.summary ? '\\n\\n' + data.summary : '') }});
                            }} else {{
                                this.messages.push({{ role: 'error', content: data.detail || 'Failed to add attraction' }});
                            }}
                        }} catch (e) {{
                            this.messages.push({{ role: 'error', content: 'Error: ' + e.message }});
                        }}
                        this.loading = false;
                        this.persist();
                        this.scrollToBottom();
                        return;
                    }} else if (skill.action) {{
                        var result = await this.executeActions([{{type: skill.action, data: skill.data}}]);
                        this.messages.push({{ role: 'assistant', content: result || 'Done.' }});
                    }} else {{
                        this.messages.push({{ role: 'assistant', content: skill.response }});
                    }}
                    this.persist();
                    this.scrollToBottom();
                    return;
                }}
            }}

            this.loading = true;
            this.persist();

            try {{
                var apiMessages = this.messages.filter(function(m) {{ return m.role === 'user' || m.role === 'assistant'; }}).map(function(m) {{
                    return {{ role: m.role, content: m.content }};
                }});
                var resp = await fetch('/api/chat', {{
                    method: 'POST',
                    headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify({{ messages: apiMessages }})
                }});
                if (!resp.ok) {{
                    var err = await resp.json().catch(function() {{ return {{detail: 'Chat unavailable'}}; }});
                    this.messages.push({{ role: 'error', content: err.detail || 'Something went wrong' }});
                }} else {{
                    var data = await resp.json();
                    this.messages.push({{ role: 'assistant', content: data.content }});
                    if (data.action_results && data.action_results.length > 0) {{
                        this.messages.push({{ role: 'assistant', content: data.action_results.join('\\n') }});
                    }}
                    if (data.trip_changed) {{
                        await Alpine.store('trip').reload();
                    }}
                }}
            }} catch (e) {{
                this.messages.push({{ role: 'error', content: 'Network error: ' + e.message }});
            }}
            this.loading = false;
            this.persist();
            this.scrollToBottom();
        }},
        async executeActions(actions) {{
            var store = Alpine.store('trip');
            var results = [];
            for (var action of actions) {{
                try {{
                    if (action.type === 'add_attraction') {{
                        await store.addAttraction(action.data);
                        results.push('Added: ' + (action.data.name || 'attraction'));
                    }} else if (action.type === 'add_day_trip') {{
                        await store.addDayTrip(action.data);
                        results.push('Added day trip: ' + (action.data.name || ''));
                    }} else if (action.type === 'add_day') {{
                        await store.addDay(action.data);
                        results.push('Created day: ' + (action.data.date || ''));
                    }} else if (action.type === 'schedule') {{
                        var d = action.data;
                        await store.scheduleAttraction(d.attraction_id, d.date, d.start_time);
                        results.push('Scheduled: ' + d.attraction_id + ' on ' + d.date);
                    }}
                }} catch (e) {{
                    console.error('Action failed:', action, e);
                    results.push('Failed: ' + (action.data.name || action.type) + ' - ' + e.message);
                }}
            }}
            return results.length ? results.join('\\n') : '';
        }}
    }};
}}

document.addEventListener('alpine:init', function() {{
    function toast(type, message) {{
        window.dispatchEvent(new CustomEvent('toast', {{detail: {{type: type, message: message}}}}));
    }}

    Alpine.store('trip', Object.assign({{}}, window.__TRIP_DATA__, {{

        async save(field, value) {{
            var self = this;
            var result = await offlineFetch('/api/trip', {{
                method: 'PATCH',
                headers: {{'Content-Type': 'application/json'}},
                body: JSON.stringify({{[field]: value}})
            }}, function() {{
                self[field] = value;
                _persistLocal();
            }});
            if (result.ok) {{
                toast('success', result.offline ? 'Saved locally' : 'Trip updated');
            }} else {{ toast('error', 'Failed to save'); }}
            return result.resp || {{ ok: result.ok }};
        }},

        async addAttraction(data) {{
            var self = this;
            var added = false;
            await tryServerOrLocal('/api/attractions', {{
                method: 'POST',
                headers: {{'Content-Type': 'application/json'}},
                body: JSON.stringify(data)
            }}, async function(resp) {{
                var a = await resp.json();
                self.attractions.push(a);
                toast('success', 'Attraction added');
                reloadMap();
                added = true;
            }}, function() {{
                var local = Object.assign({{}}, data, {{ id: _genId() }});
                if (!local.location) local.location = {{ lat: 0, lng: 0, address: '' }};
                if (local.tags && typeof local.tags === 'string') local.tags = local.tags.split(',').map(function(t){{ return t.trim(); }});
                self.attractions.push(local);
                _persistLocal();
                toast('success', 'Saved locally');
                added = true;
            }});
            return {{ ok: added }};
        }},

        async updateAttraction(id, data) {{
            var self = this;
            var updated = false;
            await tryServerOrLocal('/api/attractions/' + id, {{
                method: 'PATCH',
                headers: {{'Content-Type': 'application/json'}},
                body: JSON.stringify(data)
            }}, async function(resp) {{
                var u = await resp.json();
                var idx = self.attractions.findIndex(function(a) {{ return a.id === id; }});
                if (idx >= 0) self.attractions[idx] = u;
                toast('success', 'Attraction updated');
                reloadMap();
                updated = true;
            }}, function() {{
                var idx = self.attractions.findIndex(function(a) {{ return a.id === id; }});
                if (idx >= 0) Object.assign(self.attractions[idx], data);
                _persistLocal();
                toast('success', 'Saved locally');
                updated = true;
            }});
            return {{ ok: updated }};
        }},

        async deleteAttraction(id) {{
            var self = this;
            var deleted = false;
            await tryServerOrLocal('/api/attractions/' + id, {{
                method: 'DELETE'
            }}, async function(resp) {{
                self.attractions = self.attractions.filter(function(a) {{ return a.id !== id; }});
                toast('success', 'Attraction deleted');
                reloadMap();
                deleted = true;
            }}, function() {{
                self.attractions = self.attractions.filter(function(a) {{ return a.id !== id; }});
                _persistLocal();
                toast('success', 'Deleted locally');
                deleted = true;
            }});
            return {{ ok: deleted }};
        }},

        async setScore(id, score) {{
            var self = this;
            var result = await offlineFetch('/api/attractions/' + id + '/score', {{
                method: 'POST',
                headers: {{'Content-Type': 'application/json'}},
                body: JSON.stringify({{score: score}})
            }}, function() {{
                var idx = self.attractions.findIndex(function(a) {{ return a.id === id; }});
                if (idx >= 0) self.attractions[idx].user_score = score;
                _persistLocal();
            }});
            if (result.ok) reloadMap();
        }},

        async updatePreferences(prefs) {{
            var self = this;
            var result = await offlineFetch('/api/trip/preferences', {{
                method: 'PUT',
                headers: {{'Content-Type': 'application/json'}},
                body: JSON.stringify(prefs)
            }}, function() {{
                self.preferences = prefs;
                _persistLocal();
            }});
            if (result.ok) toast('success', result.offline ? 'Saved locally' : 'Preferences updated');
            else toast('error', 'Failed to update preferences');
        }},

        async addDayTrip(data) {{
            var self = this;
            var added = false;
            await tryServerOrLocal('/api/day-trips', {{ method: 'POST', headers: {{'Content-Type': 'application/json'}}, body: JSON.stringify(data) }},
            async function(resp) {{ var dt = await resp.json(); self.day_trips.push(dt); toast('success', 'Day trip added'); reloadMap(); added = true; }},
            function() {{
                var local = Object.assign({{}}, data, {{ id: _genId() }});
                if (!local.location) local.location = {{ lat: 0, lng: 0, address: '' }};
                self.day_trips.push(local);
                _persistLocal(); toast('success', 'Saved locally'); added = true;
            }});
            return {{ ok: added }};
        }},

        async updateDayTrip(id, data) {{
            var self = this;
            var ok = false;
            await tryServerOrLocal('/api/day-trips/' + id, {{ method: 'PATCH', headers: {{'Content-Type': 'application/json'}}, body: JSON.stringify(data) }},
            async function(resp) {{ var u = await resp.json(); var idx = self.day_trips.findIndex(function(d) {{ return d.id === id; }}); if (idx >= 0) self.day_trips[idx] = u; toast('success', 'Day trip updated'); reloadMap(); ok = true; }},
            function() {{
                var idx = self.day_trips.findIndex(function(d) {{ return d.id === id; }});
                if (idx >= 0) Object.assign(self.day_trips[idx], data);
                _persistLocal(); toast('success', 'Saved locally'); ok = true;
            }});
            return {{ ok: ok }};
        }},

        async deleteDayTrip(id) {{
            var self = this;
            var ok = false;
            await tryServerOrLocal('/api/day-trips/' + id, {{ method: 'DELETE' }},
            async function(resp) {{ self.day_trips = self.day_trips.filter(function(d) {{ return d.id !== id; }}); toast('success', 'Day trip deleted'); reloadMap(); ok = true; }},
            function() {{
                self.day_trips = self.day_trips.filter(function(d) {{ return d.id !== id; }});
                _persistLocal(); toast('success', 'Deleted locally'); ok = true;
            }});
            return {{ ok: ok }};
        }},

        async setDayTripScore(id, score) {{
            var self = this;
            var result = await offlineFetch('/api/day-trips/' + id + '/score', {{
                method: 'POST', headers: {{'Content-Type':'application/json'}},
                body: JSON.stringify({{score: score}})
            }}, function() {{
                var idx = self.day_trips.findIndex(function(d) {{ return d.id === id; }});
                if (idx >= 0) self.day_trips[idx].user_score = score;
                _persistLocal();
            }});
            if (result.ok) reloadMap();
        }},

        // ---- Grouping methods ----
        async addGrouping(data) {{
            var self = this;
            var ok = false;
            var created = null;
            await tryServerOrLocal('/api/groupings', {{
                method: 'POST', headers: {{'Content-Type':'application/json'}},
                body: JSON.stringify(data)
            }}, async function(resp) {{
                var g = await resp.json();
                if (!self.groupings) self.groupings = [];
                self.groupings.push(g);
                toast('success', 'Grouping created');
                ok = true; created = g;
            }}, function() {{
                var local = Object.assign({{}}, data, {{ id: _genId(), member_ids: data.member_ids || [] }});
                if (!self.groupings) self.groupings = [];
                self.groupings.push(local);
                _persistLocal(); toast('success', 'Saved locally'); ok = true; created = local;
            }});
            return {{ ok: ok, grouping: created }};
        }},
        async updateGrouping(id, data) {{
            var self = this;
            await tryServerOrLocal('/api/groupings/' + id, {{
                method: 'PATCH', headers: {{'Content-Type':'application/json'}},
                body: JSON.stringify(data)
            }}, async function(resp) {{
                var updated = await resp.json();
                var idx = (self.groupings || []).findIndex(function(g) {{ return g.id === id; }});
                if (idx >= 0) self.groupings[idx] = updated;
                toast('success', 'Grouping updated');
            }}, function() {{
                var idx = (self.groupings || []).findIndex(function(g) {{ return g.id === id; }});
                if (idx >= 0) Object.assign(self.groupings[idx], data);
                _persistLocal(); toast('success', 'Saved locally');
            }});
        }},
        async deleteGrouping(id) {{
            var self = this;
            await tryServerOrLocal('/api/groupings/' + id, {{ method: 'DELETE' }},
            async function() {{
                self.groupings = (self.groupings || []).filter(function(g) {{ return g.id !== id; }});
                // Clear parent_id on orphaned children
                (self.groupings || []).forEach(function(g) {{ if (g.parent_id === id) g.parent_id = null; }});
                toast('success', 'Grouping deleted');
            }}, function() {{
                self.groupings = (self.groupings || []).filter(function(g) {{ return g.id !== id; }});
                _persistLocal(); toast('success', 'Deleted locally');
            }});
        }},
        async toggleGroupingMember(groupingId, attractionId) {{
            var self = this;
            var grouping = (self.groupings || []).find(function(g) {{ return g.id === groupingId; }});
            if (!grouping) return;
            var idx = grouping.member_ids.indexOf(attractionId);
            if (idx >= 0) {{
                // Remove
                await tryServerOrLocal('/api/groupings/' + groupingId + '/members/' + attractionId, {{ method: 'DELETE' }},
                async function() {{ grouping.member_ids.splice(idx, 1); }},
                function() {{ grouping.member_ids.splice(idx, 1); _persistLocal(); }});
            }} else {{
                // Add
                await tryServerOrLocal('/api/groupings/' + groupingId + '/members/' + attractionId, {{ method: 'POST' }},
                async function() {{ grouping.member_ids.push(attractionId); }},
                function() {{ grouping.member_ids.push(attractionId); _persistLocal(); }});
            }}
        }},
        getGroupingsForAttraction(id) {{
            return (this.groupings || []).filter(function(g) {{ return g.member_ids && g.member_ids.includes(id); }});
        }},
        getAllMemberIds(groupingId) {{
            var self = this;
            var grouping = (self.groupings || []).find(function(g) {{ return g.id === groupingId; }});
            if (!grouping) return [];
            var ids = [].concat(grouping.member_ids || []);
            // Add members from child groupings recursively
            (self.groupings || []).forEach(function(g) {{
                if (g.parent_id === groupingId) {{
                    ids = ids.concat(self.getAllMemberIds(g.id));
                }}
            }});
            return ids;
        }},

        async addDay(data) {{
            var self = this;
            var ok = false;
            await tryServerOrLocal('/api/days', {{ method: 'POST', headers: {{'Content-Type':'application/json'}}, body: JSON.stringify(data) }},
            async function(resp) {{
                var d = await resp.json();
                self.days.push(d);
                self.days.sort(function(a, b) {{ return a.date.localeCompare(b.date); }});
                toast('success', 'Day added'); ok = true;
            }}, function() {{
                var local = Object.assign({{ activities: [] }}, data, {{ id: _genId() }});
                self.days.push(local);
                self.days.sort(function(a, b) {{ return a.date.localeCompare(b.date); }});
                _persistLocal(); toast('success', 'Saved locally'); ok = true;
            }});
            return {{ ok: ok }};
        }},

        async initDays() {{
            var self = this;
            await tryServerOrLocal('/api/init-days', {{ method: 'POST' }},
            async function(resp) {{ await self.reload(); toast('success', 'Days initialized'); }},
            function() {{
                if (self.start_date && self.end_date) {{
                    var start = new Date(self.start_date + 'T00:00:00');
                    var end = new Date(self.end_date + 'T00:00:00');
                    var existingDates = new Set((self.days || []).map(function(d) {{ return d.date; }}));
                    for (var d = new Date(start); d <= end; d.setDate(d.getDate() + 1)) {{
                        var ds = d.toISOString().split('T')[0];
                        if (!existingDates.has(ds)) {{
                            self.days.push({{ id: _genId(), date: ds, label: null, notes: null, activities: [] }});
                        }}
                    }}
                    self.days.sort(function(a, b) {{ return a.date.localeCompare(b.date); }});
                    _persistLocal(); toast('success', 'Days initialized locally');
                }} else {{ toast('error', 'Set trip dates first'); }}
            }});
        }},

        async addActivity(dayDate, data) {{
            var self = this;
            var ok = false;
            await tryServerOrLocal('/api/days/' + dayDate + '/activities', {{ method: 'POST', headers: {{'Content-Type':'application/json'}}, body: JSON.stringify(data) }},
            async function(resp) {{ await self.reload(); toast('success', 'Activity added'); ok = true; }},
            function() {{
                var day = (self.days || []).find(function(d) {{ return d.date === dayDate; }});
                if (day) {{
                    var act = Object.assign({{}}, data, {{ id: _genId() }});
                    if (!day.activities) day.activities = [];
                    day.activities.push(act);
                    _persistLocal(); toast('success', 'Saved locally');
                }}
                ok = true;
            }});
            return {{ ok: ok }};
        }},

        async deleteActivity(dayDate, activityId) {{
            var self = this;
            await tryServerOrLocal('/api/days/' + dayDate + '/activities/' + activityId, {{ method: 'DELETE' }},
            async function(resp) {{ await self.reload(); toast('success', 'Activity removed'); }},
            function() {{
                var day = (self.days || []).find(function(d) {{ return d.date === dayDate; }});
                if (day) {{
                    day.activities = (day.activities || []).filter(function(a) {{ return a.id !== activityId; }});
                    _persistLocal(); toast('success', 'Removed locally');
                }}
            }});
        }},

        async scheduleAttraction(attractionId, date, startTime) {{
            var self = this;
            var body = {{ attraction_id: attractionId, date: date }};
            if (startTime) body.start_time = startTime;
            await tryServerOrLocal('/api/schedule', {{ method: 'POST', headers: {{'Content-Type':'application/json'}}, body: JSON.stringify(body) }},
            async function(resp) {{ await self.reload(); toast('success', 'Attraction scheduled'); }},
            function() {{
                var day = (self.days || []).find(function(d) {{ return d.date === date; }});
                var attr = (self.attractions || []).find(function(a) {{ return a.id === attractionId; }});
                if (day && attr) {{
                    if (!day.activities) day.activities = [];
                    day.activities.push({{
                        id: _genId(),
                        attraction_id: attractionId,
                        name: attr.name,
                        category: attr.category,
                        duration_minutes: attr.duration_minutes || 60,
                        price_eur: attr.price_eur || 0,
                        start_time: startTime || null,
                        status: 'planned'
                    }});
                    _persistLocal(); toast('success', 'Scheduled locally');
                }}
            }});
        }},

        async reorderActivities(dayDate, activityIds) {{
            var self = this;
            await tryServerOrLocal('/api/days/' + dayDate + '/activities/reorder', {{
                method: 'PUT',
                headers: {{'Content-Type': 'application/json'}},
                body: JSON.stringify({{activity_ids: activityIds}})
            }}, async function(resp) {{ /* server handled it */ }},
            function() {{
                var day = (self.days || []).find(function(d) {{ return d.date === dayDate; }});
                if (day && day.activities) {{
                    var byId = {{}};
                    day.activities.forEach(function(a) {{ byId[a.id] = a; }});
                    day.activities = activityIds.map(function(id) {{ return byId[id]; }}).filter(Boolean);
                    _persistLocal();
                }}
            }});
        }},

        async swapDays(date1, date2) {{
            var self = this;
            if (!date1 || !date2) return;
            await tryServerOrLocal('/api/days/swap', {{
                method: 'POST',
                headers: {{'Content-Type': 'application/json'}},
                body: JSON.stringify({{date1: date1, date2: date2}})
            }}, async function(resp) {{ await self.reload(); toast('success', 'Days swapped'); }},
            function() {{
                var d1 = (self.days || []).find(function(d) {{ return d.date === date1; }});
                var d2 = (self.days || []).find(function(d) {{ return d.date === date2; }});
                if (d1 && d2) {{
                    var tmp = d1.activities; d1.activities = d2.activities; d2.activities = tmp;
                    var tmpL = d1.label; d1.label = d2.label; d2.label = tmpL;
                    var tmpN = d1.notes; d1.notes = d2.notes; d2.notes = tmpN;
                    _persistLocal(); toast('success', 'Swapped locally');
                }}
            }});
        }},

        async moveActivity(activityId, targetDate) {{
            var self = this;
            await tryServerOrLocal('/api/activities/move', {{
                method: 'POST',
                headers: {{'Content-Type': 'application/json'}},
                body: JSON.stringify({{activity_id: activityId, target_date: targetDate}})
            }}, async function(resp) {{ await self.reload(); }},
            function() {{
                var act = null;
                (self.days || []).forEach(function(d) {{
                    var idx = (d.activities || []).findIndex(function(a) {{ return a.id === activityId; }});
                    if (idx >= 0) act = d.activities.splice(idx, 1)[0];
                }});
                if (act) {{
                    var target = (self.days || []).find(function(d) {{ return d.date === targetDate; }});
                    if (target) {{
                        if (!target.activities) target.activities = [];
                        target.activities.push(act);
                        _persistLocal();
                    }}
                }}
            }});
        }},

        getActiveItinerary() {{
            var id = this.active_itinerary_id;
            var itins = this.itineraries || [];
            for (var i = 0; i < itins.length; i++) {{
                if (itins[i].id === id) return itins[i];
            }}
            return itins[0] || null;
        }},

        getActiveDays() {{
            var itin = this.getActiveItinerary();
            return itin ? itin.days : [];
        }},

        async switchItinerary(id) {{
            this.active_itinerary_id = id;
            try {{
                await fetch('/api/itineraries/' + id + '/activate', {{ method: 'POST' }});
            }} catch(e) {{}}
            await this.reload();
        }},

        async createItinerary(name, cloneFromId, description) {{
            var self = this;
            var body = {{ name: name }};
            if (cloneFromId) body.clone_from = cloneFromId;
            if (description) body.description = description;
            try {{
                var resp = await fetch('/api/itineraries', {{
                    method: 'POST',
                    headers: {{'Content-Type': 'application/json'}},
                    body: JSON.stringify(body)
                }});
                if (resp.ok) {{
                    var itin = await resp.json();
                    self.itineraries.push(itin);
                    self.active_itinerary_id = itin.id;
                    await self.reload();
                    toast('success', 'Itinerary "' + name + '" created');
                    return {{ ok: true, itinerary: itin }};
                }}
            }} catch(e) {{}}
            toast('error', 'Failed to create itinerary');
            return {{ ok: false }};
        }},

        async updateItinerary(id, data) {{
            var self = this;
            try {{
                var resp = await fetch('/api/itineraries/' + id, {{
                    method: 'PATCH',
                    headers: {{'Content-Type': 'application/json'}},
                    body: JSON.stringify(data)
                }});
                if (resp.ok) {{
                    for (var i = 0; i < self.itineraries.length; i++) {{
                        if (self.itineraries[i].id === id) {{
                            if (data.name !== undefined) self.itineraries[i].name = data.name;
                            if (data.description !== undefined) self.itineraries[i].description = data.description;
                            break;
                        }}
                    }}
                    toast('success', 'Itinerary updated');
                }}
            }} catch(e) {{ toast('error', 'Failed to update'); }}
        }},

        async deleteItinerary(id) {{
            var self = this;
            if (self.itineraries.length <= 1) {{
                toast('error', 'Cannot delete the last itinerary');
                return;
            }}
            try {{
                var resp = await fetch('/api/itineraries/' + id, {{ method: 'DELETE' }});
                if (resp.ok) {{
                    self.itineraries = self.itineraries.filter(function(it) {{ return it.id !== id; }});
                    if (self.active_itinerary_id === id) {{
                        self.active_itinerary_id = self.itineraries[0].id;
                    }}
                    await self.reload();
                    toast('success', 'Itinerary deleted');
                }}
            }} catch(e) {{ toast('error', 'Failed to delete'); }}
        }},

        async cloneItinerary(id) {{
            var self = this;
            try {{
                var resp = await fetch('/api/itineraries/' + id + '/clone', {{ method: 'POST' }});
                if (resp.ok) {{
                    var itin = await resp.json();
                    self.itineraries.push(itin);
                    self.active_itinerary_id = itin.id;
                    await self.reload();
                    toast('success', 'Itinerary cloned');
                    return {{ ok: true, itinerary: itin }};
                }}
            }} catch(e) {{}}
            toast('error', 'Failed to clone');
            return {{ ok: false }};
        }},

        async reload() {{
            try {{
                var resp = await fetch('/api/trip');
                if (resp.ok) {{ Object.assign(this, await resp.json()); return; }}
            }} catch(e) {{}}
            // Offline: nothing to reload, local state is current
        }},

        exportTrip() {{
            var data = {{}};
            ['id','name','destination','start_date','end_date','travelers','budget_eur',
             'attractions','days','day_trips','preferences','travel_segments',
             'itineraries','active_itinerary_id','groupings'].forEach(function(f) {{
                var val = Alpine.store('trip')[f];
                if (val !== undefined) data[f] = JSON.parse(JSON.stringify(val));
            }});
            var blob = new Blob([JSON.stringify(data, null, 2)], {{type: 'application/json'}});
            var a = document.createElement('a');
            a.href = URL.createObjectURL(blob);
            a.download = (data.destination || 'trip').toLowerCase().replace(/\\s+/g, '-') + '-trip.json';
            a.click();
            URL.revokeObjectURL(a.href);
            toast('success', 'Trip exported');
        }},

        importTrip(file) {{
            var self = this;
            var reader = new FileReader();
            reader.onload = function(e) {{
                try {{
                    var data = JSON.parse(e.target.result);
                    if (!data.destination) {{ toast('error', 'Invalid trip file'); return; }}
                    Object.assign(self, data);
                    _persistLocal();
                    toast('success', 'Trip imported');
                }} catch(err) {{
                    toast('error', 'Failed to parse file');
                }}
            }};
            reader.readAsText(file);
        }},

        clearLocal() {{
            var key = 'vacationeer_trip_' + (this.id || 'default');
            localStorage.removeItem(key);
            Object.assign(this, window.__TRIP_DATA__);
            toast('success', 'Local changes cleared');
        }}
    }}));
}});
</script>

<div class="app">

    <aside class="sidebar">
        <div class="sidebar-header">
            <div class="brand">Vacationeer</div>
            <div class="trip-picker">
                <button class="trip-picker-btn" id="tp-btn">
                    <span class="tp-label">{esc(trip.destination)}</span>
                    <span class="tp-chevron">&#9660;</span>
                </button>
                <div class="tp-dropdown" id="tp-dropdown">
                    <div id="tp-list"></div>
                    <div class="tp-divider"></div>
                    <button class="tp-item tp-new" onclick="document.getElementById('tp-dropdown').classList.remove('open'); window.dispatchEvent(new CustomEvent('open-modal', {{detail: 'new-trip-guide'}}));">
                        + New trip
                    </button>
                    <div class="tp-divider"></div>
                    <div style="display:flex;gap:4px;padding:6px 12px;">
                        <button onclick="Alpine.store('trip').exportTrip(); document.getElementById('tp-dropdown').classList.remove('open');"
                                style="flex:1;padding:5px 0;border:1px solid rgba(255,255,255,.15);background:rgba(255,255,255,.06);color:rgba(255,255,255,.6);border-radius:5px;cursor:pointer;font-size:10px;font-family:inherit;"
                                title="Download trip as JSON">\u2B07 Export</button>
                        <label style="flex:1;padding:5px 0;border:1px solid rgba(255,255,255,.15);background:rgba(255,255,255,.06);color:rgba(255,255,255,.6);border-radius:5px;cursor:pointer;font-size:10px;text-align:center;font-family:inherit;"
                               title="Import trip from JSON">\u2B06 Import
                            <input type="file" accept=".json" style="display:none"
                                   onchange="if(this.files[0]) Alpine.store('trip').importTrip(this.files[0]); this.value='';">
                        </label>
                    </div>
                </div>
            </div>
        </div>
        <ul class="nav">
            <li><button class="nav-btn active" data-tab="tab-map"><span class="icon">\U0001f5fa</span><span class="label">Map</span></button></li>
            <li><button class="nav-btn" data-tab="tab-overview"><span class="icon">\U0001f4cb</span><span class="label">Overview</span></button></li>
            <li><button class="nav-btn" data-tab="tab-timeline"><span class="icon">\U0001f4c5</span><span class="label">Timeline</span></button></li>
        </ul>
        <div class="sidebar-chat" x-data="sidebarChat()">
            <div class="chat-header" style="display:flex;align-items:center;justify-content:space-between;">
                <span>Assistant</span>
                <button @click="clearChat()" style="background:none;border:none;color:rgba(255,255,255,.4);cursor:pointer;font-size:10px;padding:2px 6px;" title="Clear chat">Clear</button>
            </div>
            <div class="chat-messages" x-ref="chatMessages">
                <template x-for="(msg, i) in messages" :key="i">
                    <div class="chat-bubble" :class="msg.role" x-html="msg.role === 'user' ? msg.content : renderMd(msg.content)"></div>
                </template>
                <template x-if="loading">
                    <div class="chat-bubble assistant"><span class="typing">Thinking...</span></div>
                </template>
            </div>
            <div class="chat-input">
                <input type="text" x-model="input" placeholder="Ask the assistant..."
                       @keydown.enter="send()" :disabled="loading" />
                <button @click="send()" :disabled="loading || !input.trim()">Send</button>
            </div>
        </div>
    </aside>

    <div class="main">
        <header class="header">
            <div class="header-title-row" onclick="window.dispatchEvent(new CustomEvent('open-modal', {{detail: 'edit-trip'}}))">
                <h1>{esc(trip.name)}</h1>
                <span class="edit-icon">\u270f\ufe0f</span>
            </div>
            <div class="meta" style="cursor:pointer" onclick="window.dispatchEvent(new CustomEvent('open-modal', {{detail: 'edit-trip'}}))">
                <span>\U0001f4cd {esc(trip.destination)}</span>
                <span>\U0001f4c6 {start} &ndash; {end} ({num_days} days)</span>
                <span>\U0001f465 {trip.travelers} travelers</span>
                {_budget_span(trip)}
            </div>
        </header>
        <div class="content">
            <!-- Pipeline progress banner (hidden by default, shown by JS when pipeline is active) -->
            <div id="pipeline-banner" style="display:none;background:linear-gradient(135deg,#1a2332,#2c3e50);color:#fff;padding:14px 24px;font-size:13px;">
                <div style="display:flex;align-items:center;gap:10px;">
                    <span style="display:inline-block;width:16px;height:16px;border:2px solid rgba(255,255,255,0.3);border-top:2px solid #fff;border-radius:50%;animation:pp-spin 1s linear infinite;"></span>
                    <span class="pp-step">Working...</span>
                </div>
                <div style="margin-top:8px;height:4px;background:rgba(255,255,255,0.2);border-radius:2px;overflow:hidden;">
                    <div class="pp-bar" style="height:100%;width:0%;background:#27AE60;border-radius:2px;transition:width 0.5s ease;"></div>
                </div>
            </div>
            <style>@keyframes pp-spin {{ to {{ transform: rotate(360deg); }} }}</style>
            <div id="tab-map" class="tab-panel active">
                <iframe src="{esc(map_filename)}"></iframe>
            </div>
            <div id="tab-overview" class="tab-panel">
                <div id="overview-content">{overview_inner if overview_inner else '<div class="tab-placeholder">Overview will appear here.</div>'}</div>
            </div>
            <div id="tab-timeline" class="tab-panel">
                <div id="timeline-content">{timeline_inner if timeline_inner else '<div class="tab-placeholder">Timeline will appear here.</div>'}</div>
            </div>
        </div>
    </div>

</div>

<!-- Floating add button -->
<div class="fab-container" x-data="{{ open: false }}">
    <button class="fab" @click="if (window.__activeTab === 'tab-timeline') {{ window.dispatchEvent(new CustomEvent('open-modal', {{detail: 'add-day'}})); }} else {{ open = !open; }}" :class="open && 'fab-active'" title="Add...">+</button>
    <div class="fab-menu" x-show="open" @click.outside="open = false" x-transition>
        <button @click="open=false; window.dispatchEvent(new CustomEvent('open-modal', {{detail: 'add-attraction'}}))">
            <span>\U0001f3db</span> Attraction
        </button>
        <button @click="open=false; window.dispatchEvent(new CustomEvent('open-modal', {{detail: 'add-accommodation'}}))">
            <span>\U0001f3e8</span> Accommodation
        </button>
        <button @click="open=false; window.dispatchEvent(new CustomEvent('open-modal', {{detail: 'add-transport'}}))">
            <span>\U0001f68c</span> Transport
        </button>
        <button @click="open=false; window.dispatchEvent(new CustomEvent('open-modal', {{detail: 'add-day-trip'}}))">
            <span>\U0001f682</span> Day Trip
        </button>
        <button @click="open=false; window.dispatchEvent(new CustomEvent('open-modal', {{detail: 'add-day'}}))">
            <span>\U0001f4c5</span> Day
        </button>
        <button @click="open=false; window.dispatchEvent(new CustomEvent('open-modal', {{detail: 'manage-groupings'}}))">
            <span>\U0001f3f7</span> Groupings
        </button>
    </div>
</div>

<!-- Toast notifications -->
<div class="toast-container" x-data="{{ toasts: [] }}" @toast.window="toasts.push($event.detail); setTimeout(function() {{ toasts.shift() }}, 3000)">
    <template x-for="(t, i) in toasts" :key="i">
        <div class="toast" :class="t.type" x-text="t.message"></div>
    </template>
</div>

<!-- Modals -->
<div x-data="{{ modal: null }}" @open-modal.window="modal = $event.detail" @close-modal.window="modal = null" @keydown.escape.window="modal = null">

    <!-- Add Attraction Modal -->
    <template x-if="modal === 'add-attraction'">
        <div class="modal-backdrop" @mousedown.self="modal = null">
            <div class="modal" x-data="{{
                form: {{ name: '', description: '', category: 'landmark', lat: '', lng: '', address: '', price_eur: '', duration_minutes: '', tags: [], tagInput: '', tips: '', url: '' }},
                grouping_ids: [],
                showNewGrp: false,
                newGrpName: '',
                newGrpColor: '{grouping_palette[0]}',
                grpPalette: {json.dumps(grouping_palette)},
                addTag() {{
                    var v = this.form.tagInput.replace(/,/g, '').trim();
                    if (v && !this.form.tags.includes(v)) this.form.tags.push(v);
                    this.form.tagInput = '';
                }},
                removeTag(i) {{ this.form.tags.splice(i, 1); }},
                allTags() {{
                    var s = {{}};
                    ($store.trip.attractions || []).forEach(function(a) {{ (a.tags || []).forEach(function(t) {{ s[t] = 1; }}); }});
                    return Object.keys(s).sort();
                }},
                toggleGrp(id) {{
                    var idx = this.grouping_ids.indexOf(id);
                    if (idx >= 0) this.grouping_ids.splice(idx, 1);
                    else this.grouping_ids.push(id);
                }},
                async createGrp() {{
                    if (!this.newGrpName.trim()) return;
                    var res = await $store.trip.addGrouping({{ name: this.newGrpName.trim(), color: this.newGrpColor }});
                    if (res.ok && res.grouping) this.grouping_ids.push(res.grouping.id);
                    this.newGrpName = ''; this.showNewGrp = false;
                }},
{_location_picker_xdata()}
                async submit() {{
                    if (!this.form.name.trim()) return;
                    const data = {{
                        name: this.form.name.trim(),
                        description: this.form.description.trim() || null,
                        category: this.form.category,
                        location: {{
                            lat: parseFloat(this.form.lat) || 0,
                            lng: parseFloat(this.form.lng) || 0,
                            address: this.form.address.trim() || null
                        }},
                        price_eur: this.form.price_eur ? parseFloat(this.form.price_eur) : null,
                        duration_minutes: this.form.duration_minutes ? parseInt(this.form.duration_minutes) : null,
                        tags: this.form.tags || [],
                        tips: this.form.tips.trim() || null,
                        url: this.form.url.trim() || null
                    }};
                    const resp = await $store.trip.addAttraction(data);
                    if (resp.ok) {{
                        var newAttr = $store.trip.attractions[$store.trip.attractions.length - 1];
                        if (newAttr) {{
                            for (var i = 0; i < this.grouping_ids.length; i++) {{
                                await $store.trip.toggleGroupingMember(this.grouping_ids[i], newAttr.id);
                            }}
                        }}
                        window.dispatchEvent(new CustomEvent('close-modal'));
                    }}
                }}
            }}">
                <div class="modal-header">Add Attraction</div>
                <div class="modal-body">
                    <div class="form-group">
                        <label>Name <span class="req">*</span></label>
                        <input type="text" x-model="form.name" placeholder="Attraction name" required>
                    </div>
                    <div class="form-group">
                        <label>Description</label>
                        <textarea x-model="form.description" placeholder="Brief description"></textarea>
                    </div>
                    <div class="form-group">
                        <label>Category</label>
                        <select x-model="form.category">
{category_options}
                        </select>
                    </div>
{_location_picker_html(required=True)}
                    <div class="form-row">
                        <div class="form-group">
                            <label>Price (&euro;)</label>
                            <input type="number" step="0.01" x-model="form.price_eur" placeholder="0.00">
                        </div>
                        <div class="form-group">
                            <label>Duration (min)</label>
                            <input type="number" x-model="form.duration_minutes" placeholder="60">
                        </div>
                    </div>
                    <div class="form-group">
                        <label>Tags</label>
                        <div style="display:flex;flex-wrap:wrap;gap:4px;padding:6px 10px;border:2px solid #ddd;border-radius:6px;min-height:38px;align-items:center;box-sizing:border-box;background:#fff;"
                             @click="$refs.addTagIn.focus()">
                            <template x-for="(tag, ti) in form.tags" :key="ti">
                                <span style="display:inline-flex;align-items:center;gap:3px;padding:2px 8px;border-radius:10px;background:#e8ecf1;color:#4a5568;font-size:12px;font-weight:500;">
                                    <span x-text="tag"></span>
                                    <button type="button" @click="removeTag(ti)" style="background:none;border:none;color:#999;cursor:pointer;font-size:14px;line-height:1;padding:0 2px;">&times;</button>
                                </span>
                            </template>
                            <input x-model="form.tagInput" x-ref="addTagIn"
                                   @keydown.enter.prevent="addTag()"
                                   @keydown.comma.prevent="addTag()"
                                   @keydown.backspace="if (!form.tagInput && form.tags.length) form.tags.pop()"
                                   list="add-tag-suggestions"
                                   placeholder="Add tag..."
                                   style="border:none;outline:none;font-size:13px;min-width:80px;flex:1;padding:2px 0;background:transparent;">
                            <datalist id="add-tag-suggestions">
                                <template x-for="t in allTags().filter(t => !form.tags.includes(t))" :key="t">
                                    <option :value="t"></option>
                                </template>
                            </datalist>
                        </div>
                    </div>
                    <div class="form-group" x-show="($store.trip.groupings || []).length || showNewGrp">
                        <label>Groupings</label>
                        <div style="display:flex;flex-wrap:wrap;gap:5px;align-items:center;">
                            <template x-for="grp in ($store.trip.groupings || [])" :key="grp.id">
                                <button type="button" @click="toggleGrp(grp.id)"
                                    :style="'display:inline-flex;align-items:center;padding:4px 12px;border-radius:14px;font-size:12px;font-weight:500;cursor:pointer;border:2px solid ' + (grp.color || '#888') + ';transition:all .15s;'
                                        + (grouping_ids.includes(grp.id) ? 'background:' + (grp.color || '#888') + ';color:#fff;' : 'background:#fff;color:' + (grp.color || '#888') + ';')"
                                    x-text="grp.name"></button>
                            </template>
                            <button type="button" @click="showNewGrp = !showNewGrp"
                                style="display:inline-flex;align-items:center;justify-content:center;width:28px;height:28px;border-radius:50%;border:2px dashed #aaa;background:#fff;color:#888;font-size:16px;cursor:pointer;line-height:1;"
                                title="New grouping">+</button>
                        </div>
                        <div x-show="showNewGrp" x-transition
                             style="margin-top:6px;padding:8px 10px;border:1px solid #e2e5e9;border-radius:8px;background:#fafafa;display:flex;flex-wrap:wrap;gap:6px;align-items:center;">
                            <input x-model="newGrpName" placeholder="Grouping name" @keydown.enter="createGrp()"
                                   style="flex:1;min-width:100px;padding:4px 8px;border:1px solid #ddd;border-radius:6px;font-size:13px;outline:none;">
                            <div style="display:flex;gap:3px;">
                                <template x-for="c in grpPalette.slice(0, 8)" :key="c">
                                    <button type="button" @click="newGrpColor = c"
                                        :style="'width:20px;height:20px;border-radius:50%;border:2px solid ' + (newGrpColor === c ? '#333' : 'transparent') + ';background:' + c + ';cursor:pointer;'"></button>
                                </template>
                            </div>
                            <button type="button" @click="createGrp()"
                                style="padding:4px 10px;background:#27AE60;color:#fff;border:none;border-radius:6px;font-size:12px;font-weight:600;cursor:pointer;">Add</button>
                        </div>
                    </div>
                    <div class="form-group">
                        <label>Tips</label>
                        <textarea x-model="form.tips" placeholder="Travel tips or notes"></textarea>
                    </div>
                    <div class="form-group">
                        <label>URL</label>
                        <input type="url" x-model="form.url" placeholder="https://...">
                    </div>
                    <p class="form-hint">* Required fields</p>
                    <div class="modal-actions">
                        <button class="btn btn-cancel" @click="window.dispatchEvent(new CustomEvent('close-modal'))">Cancel</button>
                        <button class="btn btn-primary" @click="submit()">Add Attraction</button>
                    </div>
                </div>
            </div>
        </div>
    </template>

    <!-- Edit Trip Modal -->
    <template x-if="modal === 'edit-trip'">
        <div class="modal-backdrop" @mousedown.self="modal = null">
            <div class="modal" x-data="{{
                form: {{
                    name: $store.trip.name,
                    destination: $store.trip.destination,
                    start_date: $store.trip.start_date,
                    end_date: $store.trip.end_date,
                    travelers: $store.trip.travelers,
                    budget_eur: $store.trip.budget_eur || ''
                }},
                async submit() {{
                    for (const [key, val] of Object.entries(this.form)) {{
                        const parsed = (key === 'travelers') ? parseInt(val) : (key === 'budget_eur' && val) ? parseFloat(val) : (key === 'budget_eur' && !val) ? null : val;
                        if (parsed !== $store.trip[key]) {{
                            await $store.trip.save(key, parsed);
                            $store.trip[key] = parsed;
                        }}
                    }}
                    window.dispatchEvent(new CustomEvent('close-modal'));
                }}
            }}">
                <div class="modal-header">Edit Trip</div>
                <div class="modal-body">
                    <div class="form-group">
                        <label>Trip Name <span class="req">*</span></label>
                        <input type="text" x-model="form.name" required>
                    </div>
                    <div class="form-group">
                        <label>Destination <span class="req">*</span></label>
                        <input type="text" x-model="form.destination" required>
                    </div>
                    <div class="form-row">
                        <div class="form-group">
                            <label>Start Date <span class="req">*</span></label>
                            <input type="date" x-model="form.start_date" required>
                        </div>
                        <div class="form-group">
                            <label>End Date <span class="req">*</span></label>
                            <input type="date" x-model="form.end_date" required>
                        </div>
                    </div>
                    <div class="form-row">
                        <div class="form-group">
                            <label>Travelers <span class="req">*</span></label>
                            <input type="number" min="1" x-model="form.travelers" required>
                        </div>
                        <div class="form-group">
                            <label>Total Budget (&euro;)</label>
                            <input type="number" step="0.01" x-model="form.budget_eur" placeholder="Optional">
                        </div>
                    </div>
                    <p class="form-hint">* Required fields</p>
                    <div class="modal-actions">
                        <button class="btn btn-cancel" @click="window.dispatchEvent(new CustomEvent('close-modal'))">Cancel</button>
                        <button class="btn btn-primary" @click="submit()">Save Changes</button>
                    </div>
                </div>
            </div>
        </div>
    </template>

    <!-- Edit Preferences Modal -->
    <template x-if="modal === 'edit-preferences'">
        <div class="modal-backdrop" @mousedown.self="modal = null">
            <div class="modal" x-data="{{
                form: {{
                    interests: ($store.trip.preferences && $store.trip.preferences.interests) ? $store.trip.preferences.interests.join(', ') : '',
                    avoid: ($store.trip.preferences && $store.trip.preferences.avoid) ? $store.trip.preferences.avoid.join(', ') : '',
                    pace: ($store.trip.preferences && $store.trip.preferences.pace) ? $store.trip.preferences.pace : 'moderate',
                    budget_per_day_eur: ($store.trip.preferences && $store.trip.preferences.budget_per_day_eur) ? $store.trip.preferences.budget_per_day_eur : ''
                }},
                async submit() {{
                    const prefs = {{
                        interests: this.form.interests ? this.form.interests.split(',').map(function(s) {{ return s.trim(); }}).filter(Boolean) : [],
                        avoid: this.form.avoid ? this.form.avoid.split(',').map(function(s) {{ return s.trim(); }}).filter(Boolean) : [],
                        pace: this.form.pace,
                        budget_per_day_eur: this.form.budget_per_day_eur ? parseFloat(this.form.budget_per_day_eur) : null
                    }};
                    await $store.trip.updatePreferences(prefs);
                    window.dispatchEvent(new CustomEvent('close-modal'));
                }}
            }}">
                <div class="modal-header">Edit Preferences</div>
                <div class="modal-body">
                    <div class="form-group">
                        <label>Interests (comma-separated)</label>
                        <input type="text" x-model="form.interests" placeholder="architecture, food, history">
                    </div>
                    <div class="form-group">
                        <label>Avoid (comma-separated)</label>
                        <input type="text" x-model="form.avoid" placeholder="crowds, long walks">
                    </div>
                    <div class="form-group">
                        <label>Pace</label>
                        <select x-model="form.pace">
{pace_options}
                        </select>
                    </div>
                    <div class="form-group">
                        <label>Budget per Day (&euro;)</label>
                        <input type="number" step="0.01" x-model="form.budget_per_day_eur" placeholder="Optional">
                    </div>
                    <div class="modal-actions">
                        <button class="btn btn-cancel" @click="window.dispatchEvent(new CustomEvent('close-modal'))">Cancel</button>
                        <button class="btn btn-primary" @click="submit()">Save Preferences</button>
                    </div>
                </div>
            </div>
        </div>
    </template>

    <!-- Add Day Trip Modal -->
    <template x-if="modal === 'add-day-trip'">
        <div class="modal-backdrop" @mousedown.self="modal = null">
            <div class="modal" x-data="{{
                form: {{ name: '', destination: '', description: '', lat: '', lng: '', address: '', total_price_eur: '', total_duration_minutes: '', tags: '', tips: '' }},
{_location_picker_xdata()}
                async submit() {{
                    if (!this.form.name.trim() || !this.form.destination.trim()) return;
                    if (!this.form.lat || !this.form.lng) return;
                    const data = {{
                        name: this.form.name.trim(),
                        destination: this.form.destination.trim(),
                        description: this.form.description.trim() || null,
                        location: {{
                            lat: parseFloat(this.form.lat) || 0,
                            lng: parseFloat(this.form.lng) || 0,
                            address: this.form.address.trim() || null
                        }},
                        total_price_eur: this.form.total_price_eur ? parseFloat(this.form.total_price_eur) : null,
                        total_duration_minutes: this.form.total_duration_minutes ? parseInt(this.form.total_duration_minutes) : null,
                        tags: this.form.tags ? this.form.tags.split(',').map(function(t) {{ return t.trim(); }}).filter(Boolean) : [],
                        tips: this.form.tips.trim() || null
                    }};
                    const resp = await $store.trip.addDayTrip(data);
                    if (resp.ok) window.dispatchEvent(new CustomEvent('close-modal'));
                }}
            }}">
                <div class="modal-header">Add Day Trip</div>
                <div class="modal-body">
                    <div class="form-group">
                        <label>Name <span class="req">*</span></label>
                        <input type="text" x-model="form.name" placeholder="Day trip name" required>
                    </div>
                    <div class="form-group">
                        <label>Destination <span class="req">*</span></label>
                        <input type="text" x-model="form.destination" placeholder="Where to?" required>
                    </div>
                    <div class="form-group">
                        <label>Description</label>
                        <textarea x-model="form.description" placeholder="Brief description"></textarea>
                    </div>
{_location_picker_html(required=True)}
                    <div class="form-row">
                        <div class="form-group">
                            <label>Total Price (&euro;)</label>
                            <input type="number" step="0.01" x-model="form.total_price_eur" placeholder="0.00">
                        </div>
                        <div class="form-group">
                            <label>Total Duration (min)</label>
                            <input type="number" x-model="form.total_duration_minutes" placeholder="60">
                        </div>
                    </div>
                    <div class="form-group">
                        <label>Tags (comma-separated)</label>
                        <input type="text" x-model="form.tags" placeholder="beach, nature, hiking">
                    </div>
                    <div class="form-group">
                        <label>Tips</label>
                        <textarea x-model="form.tips" placeholder="Travel tips or notes"></textarea>
                    </div>
                    <p class="form-hint">* Required fields</p>
                    <div class="modal-actions">
                        <button class="btn btn-cancel" @click="window.dispatchEvent(new CustomEvent('close-modal'))">Cancel</button>
                        <button class="btn btn-primary" @click="submit()">Add Day Trip</button>
                    </div>
                </div>
            </div>
        </div>
    </template>

    <!-- Add Day Modal -->
    <template x-if="modal === 'add-day'">
        <div class="modal-backdrop" @mousedown.self="modal = null">
            <div class="modal" x-data="{{
                form: {{ date: '', label: '', start_time: '', notes: '', useAI: false, aiPrompt: '' }},
                loading: false,
                async submit() {{
                    if (!this.form.date) return;
                    var existing = ($store.trip.days || []).some(function(d) {{ return d.date === this.form.date; }}.bind(this));
                    if (existing) {{
                        window.dispatchEvent(new CustomEvent('toast', {{detail: {{type:'error', message:'Day already exists for ' + this.form.date}}}}));
                        return;
                    }}
                    this.loading = true;
                    var data = {{
                        date: this.form.date,
                        label: this.form.label.trim() || null,
                        start_time: this.form.start_time || null,
                        notes: this.form.notes.trim() || null
                    }};
                    var resp = await $store.trip.addDay(data);
                    if (!resp.ok) {{ this.loading = false; return; }}
                    if (this.form.useAI && this.form.aiPrompt.trim()) {{
                        try {{
                            var aiResp = await fetch('/api/days/' + this.form.date + '/ai-plan', {{
                                method: 'POST',
                                headers: {{'Content-Type': 'application/json'}},
                                body: JSON.stringify({{ prompt: this.form.aiPrompt.trim() }})
                            }});
                            if (aiResp.ok) {{
                                var result = await aiResp.json();
                                await $store.trip.reload();
                                window.dispatchEvent(new CustomEvent('toast', {{detail: {{type:'success', message: result.activities_created + ' activities added by AI'}}}}));
                            }} else {{
                                window.dispatchEvent(new CustomEvent('toast', {{detail: {{type:'error', message:'AI planning failed — day created but empty'}}}}));
                            }}
                        }} catch(e) {{
                            window.dispatchEvent(new CustomEvent('toast', {{detail: {{type:'error', message:'AI error: ' + e.message}}}}));
                        }}
                    }}
                    this.loading = false;
                    window.dispatchEvent(new CustomEvent('close-modal'));
                }}
            }}">
                <div class="modal-header">Add Day</div>
                <div class="modal-body">
                    <div class="form-group">
                        <label>Date <span class="req">*</span></label>
                        <input type="date" x-model="form.date" required>
                    </div>
                    <div class="form-group">
                        <label>Label</label>
                        <input type="text" x-model="form.label" placeholder="e.g. Old Town Day">
                    </div>
                    <div class="form-group">
                        <label>Start Time</label>
                        <input type="time" x-model="form.start_time">
                    </div>
                    <div class="form-group">
                        <label>Notes</label>
                        <textarea x-model="form.notes" placeholder="Notes for this day"></textarea>
                    </div>
                    <div class="form-group" style="margin-top:8px">
                        <label style="display:flex;align-items:center;gap:8px;cursor:pointer">
                            <input type="checkbox" x-model="form.useAI" style="width:16px;height:16px">
                            <span>Design with AI</span>
                        </label>
                    </div>
                    <div class="form-group" x-show="form.useAI" x-transition>
                        <label>Describe the day</label>
                        <textarea x-model="form.aiPrompt" rows="3" placeholder="e.g. Relaxed morning at the beach, then explore the old town in the afternoon with a nice dinner"></textarea>
                        <p style="font-size:11px;color:#888;margin-top:4px">AI will pick activities from your unscheduled attractions and fill the day.</p>
                    </div>
                    <div class="modal-actions">
                        <button class="btn btn-cancel" @click="window.dispatchEvent(new CustomEvent('close-modal'))">Cancel</button>
                        <button class="btn btn-primary" @click="submit()" :disabled="!form.date || loading">
                            <span x-show="!loading">Add Day</span>
                            <span x-show="loading">Creating...</span>
                        </button>
                    </div>
                </div>
            </div>
        </div>
    </template>

    <!-- Add Accommodation Modal -->
    <template x-if="modal === 'add-accommodation'">
        <div class="modal-backdrop" @mousedown.self="modal = null">
            <div class="modal" x-data="{{
                form: {{ name: '', address: '', checkin: '', checkout: '', lat: '', lng: '', total_price_eur: '', description: '', tags: '', tips: '', url: '' }},
{_location_picker_xdata()}
                async submit() {{
                    if (!this.form.name.trim()) return;
                    var desc = this.form.description.trim() || '';
                    if (this.form.checkin && this.form.checkout) {{
                        desc = 'Check-in: ' + this.form.checkin + ' / Check-out: ' + this.form.checkout + (desc ? '\\n' + desc : '');
                    }} else if (this.form.checkin) {{
                        desc = 'Check-in: ' + this.form.checkin + (desc ? '\\n' + desc : '');
                    }} else if (this.form.checkout) {{
                        desc = 'Check-out: ' + this.form.checkout + (desc ? '\\n' + desc : '');
                    }}
                    const data = {{
                        name: this.form.name.trim(),
                        description: desc || null,
                        category: 'accommodation',
                        location: {{
                            lat: parseFloat(this.form.lat) || 0,
                            lng: parseFloat(this.form.lng) || 0,
                            address: this.form.address.trim() || null
                        }},
                        price_eur: this.form.total_price_eur ? parseFloat(this.form.total_price_eur) : null,
                        tags: this.form.tags ? this.form.tags.split(',').map(function(t) {{ return t.trim(); }}).filter(Boolean) : [],
                        tips: this.form.tips.trim() || null,
                        url: this.form.url.trim() || null
                    }};
                    const resp = await $store.trip.addAttraction(data);
                    if (resp.ok) {{ reloadMap(); window.dispatchEvent(new CustomEvent('close-modal')); }}
                }}
            }}">
                <div class="modal-header" style="background:#922B21;">\U0001f3e8 Add Accommodation</div>
                <div class="modal-body">
                    <div class="form-group">
                        <label>Name <span class="req">*</span></label>
                        <input type="text" x-model="form.name" placeholder="Hotel / Apartment name" required>
                    </div>
                    <div class="form-row">
                        <div class="form-group">
                            <label>Check-in Date</label>
                            <input type="date" x-model="form.checkin">
                        </div>
                        <div class="form-group">
                            <label>Check-out Date</label>
                            <input type="date" x-model="form.checkout">
                        </div>
                    </div>
{_location_picker_html(required=True)}
                    <div class="form-group">
                        <label>Total Price (&euro;)</label>
                        <input type="number" step="0.01" x-model="form.total_price_eur" placeholder="0.00">
                    </div>
                    <div class="form-group">
                        <label>Description</label>
                        <textarea x-model="form.description" placeholder="Notes about the accommodation"></textarea>
                    </div>
                    <div class="form-group">
                        <label>Tags (comma-separated)</label>
                        <input type="text" x-model="form.tags" placeholder="hotel, pool, central">
                    </div>
                    <div class="form-group">
                        <label>Tips</label>
                        <textarea x-model="form.tips" placeholder="Useful tips"></textarea>
                    </div>
                    <div class="form-group">
                        <label>URL</label>
                        <input type="url" x-model="form.url" placeholder="https://...">
                    </div>
                    <p class="form-hint">* Required fields</p>
                    <div class="modal-actions">
                        <button class="btn btn-cancel" @click="window.dispatchEvent(new CustomEvent('close-modal'))">Cancel</button>
                        <button class="btn btn-primary" @click="submit()">Add Accommodation</button>
                    </div>
                </div>
            </div>
        </div>
    </template>

    <!-- Add Transport Modal -->
    <template x-if="modal === 'add-transport'">
        <div class="modal-backdrop" @mousedown.self="modal = null">
            <div class="modal" x-data="{{
                form: {{ name: '', mode: 'train', origin: '', destination: '', departure: '', arrival: '', lat: '', lng: '', address: '', price: '', booking_ref: '', notes: '' }},
{_location_picker_xdata()}
                async submit() {{
                    if (!this.form.name.trim()) return;
                    var parts = [];
                    if (this.form.mode) parts.push('Mode: ' + this.form.mode);
                    if (this.form.origin.trim() && this.form.destination.trim()) parts.push(this.form.origin.trim() + ' \u2192 ' + this.form.destination.trim());
                    else if (this.form.origin.trim()) parts.push('From: ' + this.form.origin.trim());
                    else if (this.form.destination.trim()) parts.push('To: ' + this.form.destination.trim());
                    if (this.form.departure) parts.push('Departs: ' + this.form.departure);
                    if (this.form.arrival) parts.push('Arrives: ' + this.form.arrival);
                    if (this.form.booking_ref.trim()) parts.push('Booking: ' + this.form.booking_ref.trim());
                    if (this.form.notes.trim()) parts.push(this.form.notes.trim());
                    var tags = [this.form.mode];
                    const data = {{
                        name: this.form.name.trim(),
                        description: parts.join('\\n') || null,
                        category: 'transport',
                        location: {{
                            lat: parseFloat(this.form.lat) || 0,
                            lng: parseFloat(this.form.lng) || 0,
                            address: this.form.address.trim() || this.form.origin.trim() || null
                        }},
                        price_eur: this.form.price ? parseFloat(this.form.price) : null,
                        tags: tags,
                        tips: null,
                        url: null
                    }};
                    const resp = await $store.trip.addAttraction(data);
                    if (resp.ok) {{ reloadMap(); window.dispatchEvent(new CustomEvent('close-modal')); }}
                }}
            }}">
                <div class="modal-header" style="background:#7F8C8D;">\U0001f68c Add Transport</div>
                <div class="modal-body">
                    <div class="form-group">
                        <label>Name <span class="req">*</span></label>
                        <input type="text" x-model="form.name" placeholder="e.g. Train to Barcelona" required>
                    </div>
                    <div class="form-group">
                        <label>Mode</label>
                        <select x-model="form.mode">
                            <option value="train">Train</option>
                            <option value="bus">Bus</option>
                            <option value="metro">Metro</option>
                            <option value="car">Car</option>
                            <option value="boat">Boat</option>
                            <option value="walk">Walk</option>
                        </select>
                    </div>
                    <div class="form-row">
                        <div class="form-group">
                            <label>Origin</label>
                            <input type="text" x-model="form.origin" placeholder="Departure location">
                        </div>
                        <div class="form-group">
                            <label>Destination</label>
                            <input type="text" x-model="form.destination" placeholder="Arrival location">
                        </div>
                    </div>
                    <div class="form-row">
                        <div class="form-group">
                            <label>Departure Time</label>
                            <input type="datetime-local" x-model="form.departure">
                        </div>
                        <div class="form-group">
                            <label>Arrival Time</label>
                            <input type="datetime-local" x-model="form.arrival">
                        </div>
                    </div>
{_location_picker_html(required=False)}
                    <div class="form-group">
                        <label>Price (&euro;)</label>
                        <input type="number" step="0.01" x-model="form.price" placeholder="0.00">
                    </div>
                    <div class="form-group">
                        <label>Booking Reference</label>
                        <input type="text" x-model="form.booking_ref" placeholder="Confirmation code">
                    </div>
                    <div class="form-group">
                        <label>Notes</label>
                        <textarea x-model="form.notes" placeholder="Additional notes"></textarea>
                    </div>
                    <p class="form-hint">* Required fields</p>
                    <div class="modal-actions">
                        <button class="btn btn-cancel" @click="window.dispatchEvent(new CustomEvent('close-modal'))">Cancel</button>
                        <button class="btn btn-primary" @click="submit()">Add Transport</button>
                    </div>
                </div>
            </div>
        </div>
    </template>

    <!-- New Trip Guide Modal -->
    <template x-if="modal === 'new-trip-guide'">
        <div class="modal-backdrop" @mousedown.self="modal = null">
            <div class="modal" style="max-width:560px" x-data="newTripForm()">
                <div class="modal-header">
                    <h2 x-text="phase === 'form' ? 'Create a New Trip' : 'Creating Trip...'"></h2>
                    <button class="modal-close" @click="cleanup(); window.dispatchEvent(new CustomEvent('close-modal'))">&times;</button>
                </div>

                <!-- Form phase -->
                <template x-if="phase === 'form'">
                    <div>
                        <div class="modal-body">
                            <div class="form-group">
                                <label>Destination <span class="req">*</span></label>
                                <input type="text" x-model="form.destination" placeholder="e.g. Rome, Italy" required>
                            </div>
                            <div class="form-group">
                                <label>Trip Name</label>
                                <input type="text" x-model="form.name" :placeholder="form.destination ? form.destination.split(',')[0].trim() + ' 2026' : 'Auto-generated'">
                            </div>
                            <div class="form-row">
                                <div class="form-group">
                                    <label>Start Date <span class="req">*</span></label>
                                    <input type="date" x-model="form.start_date">
                                </div>
                                <div class="form-group">
                                    <label>End Date <span class="req">*</span></label>
                                    <input type="date" x-model="form.end_date">
                                </div>
                            </div>
                            <div class="form-row">
                                <div class="form-group">
                                    <label>Travelers</label>
                                    <input type="number" x-model="form.travelers" min="1" max="20">
                                </div>
                                <div class="form-group">
                                    <label>Budget (EUR)</label>
                                    <input type="number" x-model="form.budget_eur" placeholder="Optional" step="100">
                                </div>
                            </div>
                            <div class="form-group">
                                <label>Interests</label>
                                <input type="text" x-model="form.interests_str" placeholder="history, food, art, nature...">
                            </div>
                            <div class="form-row">
                                <div class="form-group">
                                    <label>Pace</label>
                                    <select x-model="form.pace">
                                        <option value="relaxed">Relaxed</option>
                                        <option value="moderate" selected>Moderate</option>
                                        <option value="fast">Fast</option>
                                    </select>
                                </div>
                                <div class="form-group">
                                    <label>Day Trips</label>
                                    <select x-model="form.include_day_trips">
                                        <option value="true">Yes</option>
                                        <option value="false">No</option>
                                    </select>
                                </div>
                            </div>
                            <div class="form-group">
                                <label>Must-do</label>
                                <input type="text" x-model="form.must_do" placeholder="e.g. Colosseum, authentic carbonara">
                            </div>
                            <div class="form-group">
                                <label>Context</label>
                                <input type="text" x-model="form.context" placeholder="e.g. anniversary trip, with kids">
                            </div>
                            <p style="margin-top:8px;font-size:12px;color:#888">
                                AI will research your destination in the background. You can keep browsing.
                            </p>
                        </div>
                        <div class="modal-actions">
                            <button class="btn btn-cancel" @click="window.dispatchEvent(new CustomEvent('close-modal'))">Cancel</button>
                            <button class="btn btn-primary" @click="submit()" :disabled="!form.destination || !form.start_date || !form.end_date">
                                Start Research
                            </button>
                        </div>
                    </div>
                </template>

                <!-- Progress phase -->
                <template x-if="phase === 'progress'">
                    <div class="modal-body" style="padding:24px">
                        <div style="text-align:center;margin-bottom:20px">
                            <div style="font-size:32px;margin-bottom:8px" x-text="statusIcon()"></div>
                            <div style="font-size:15px;font-weight:600;color:#1a2332" x-text="job.step || 'Starting...'"></div>
                            <div style="font-size:13px;color:#888;margin-top:4px" x-text="job.slug"></div>
                        </div>
                        <div style="background:#f5f6f8;border-radius:8px;overflow:hidden;height:6px;margin-bottom:16px">
                            <div style="height:100%;border-radius:8px;transition:width 0.5s ease"
                                 :style="'width:' + progressPct() + '%; background:' + (job.status === 'error' ? '#dc2626' : job.status === 'done' ? '#059669' : '#4ea4f6')">
                            </div>
                        </div>
                        <div style="display:flex;justify-content:space-between;font-size:12px;color:#888">
                            <span :class="{{ 'font-weight:600;color:#1a2332': job.status === 'researching' }}"
                                  :style="progressStepStyle('researching')">Research</span>
                            <span :style="progressStepStyle('converting')">Convert</span>
                            <span :style="progressStepStyle('building')">Build</span>
                            <span :style="progressStepStyle('done')">Done</span>
                        </div>
                        <template x-if="job.status === 'error'">
                            <div style="margin-top:16px;padding:12px;background:#fef2f2;border-radius:8px;color:#dc2626;font-size:13px">
                                <strong>Error:</strong> <span x-text="job.error"></span>
                            </div>
                        </template>
                        <template x-if="job.status === 'done'">
                            <div style="margin-top:16px;padding:12px;background:#f0fdf4;border-radius:8px;color:#059669;font-size:13px">
                                Trip ready! <span x-text="job.attractions_count"></span> attractions, <span x-text="job.day_trips_count"></span> day trips.
                            </div>
                        </template>
                        <div class="modal-actions" style="margin-top:16px">
                            <button class="btn btn-cancel" @click="cleanup(); window.dispatchEvent(new CustomEvent('close-modal'))">
                                <span x-text="job.status === 'done' || job.status === 'error' ? 'Close' : 'Dismiss (keeps running)'"></span>
                            </button>
                            <template x-if="job.status === 'done' && job.app_url">
                                <button class="btn btn-primary" @click="window.location.href = job.app_url">
                                    Open Trip
                                </button>
                            </template>
                        </div>
                    </div>
                </template>
            </div>
        </div>
    </template>

    <!-- Manage Groupings Modal -->
    <template x-if="modal === 'manage-groupings'">
        <div class="modal-backdrop" @mousedown.self="modal = null">
            <div class="modal" style="max-width:560px" x-data="{{
                mode: 'list',
                editId: null,
                form: {{ name: '', description: '', color: '', parent_id: '' }},
                palette: {json.dumps(grouping_palette)},
                init() {{ this.form.color = this.palette[0]; }},
                resetForm() {{
                    this.form = {{ name: '', description: '', color: this.palette[0], parent_id: '' }};
                    this.editId = null;
                    this.mode = 'form';
                }},
                editGrouping(g) {{
                    this.form = {{ name: g.name, description: g.description || '', color: g.color, parent_id: g.parent_id || '' }};
                    this.editId = g.id;
                    this.mode = 'form';
                }},
                async saveGrouping() {{
                    if (!this.form.name.trim()) return;
                    var data = {{
                        name: this.form.name.trim(),
                        description: this.form.description.trim() || null,
                        color: this.form.color,
                        parent_id: this.form.parent_id || null
                    }};
                    if (this.editId) {{
                        await $store.trip.updateGrouping(this.editId, data);
                    }} else {{
                        await $store.trip.addGrouping(data);
                    }}
                    this.mode = 'list';
                    this.editId = null;
                }},
                async removeGrouping(id) {{
                    if (confirm('Delete this grouping?')) {{
                        await $store.trip.deleteGrouping(id);
                    }}
                }},
                isDescendant(gid, ancestorId) {{
                    if (!ancestorId) return false;
                    var visited = {{}};
                    var cur = gid;
                    while (cur) {{
                        if (cur === ancestorId) return true;
                        if (visited[cur]) return false;
                        visited[cur] = true;
                        var p = ($store.trip.groupings || []).find(function(x) {{ return x.id === cur; }});
                        cur = p ? p.parent_id : null;
                    }}
                    return false;
                }},
                getGrouping(id) {{
                    return ($store.trip.groupings || []).find(function(g) {{ return g.id === id; }});
                }}
            }}">
                <div class="modal-header" style="display:flex;align-items:center;justify-content:space-between">
                    <span x-text="mode === 'list' ? 'Groupings' : (editId ? 'Edit Grouping' : 'New Grouping')"></span>
                    <button @click="window.dispatchEvent(new CustomEvent('close-modal'))" style="background:none;border:none;color:#fff;font-size:22px;cursor:pointer;padding:0 4px;line-height:1">&times;</button>
                </div>
                <div class="modal-body">
                    <!-- List view -->
                    <template x-if="mode === 'list'">
                        <div>
                            <template x-if="!($store.trip.groupings || []).length">
                                <p style="color:#888;text-align:center;padding:20px 0">No groupings yet. Create one to organize your attractions.</p>
                            </template>
                            <template x-for="g in ($store.trip.groupings || [])" :key="g.id">
                                <div style="display:flex;align-items:center;gap:10px;padding:10px 0;border-bottom:1px solid #eee">
                                    <span :style="'width:14px;height:14px;border-radius:50%;flex-shrink:0;background:' + g.color" style="display:inline-block"></span>
                                    <div style="flex:1;min-width:0">
                                        <div style="font-weight:600;font-size:14px" x-text="g.name"></div>
                                        <div style="font-size:12px;color:#888" x-text="(g.member_ids || []).length + ' attractions'"></div>
                                    </div>
                                    <button style="background:none;border:none;cursor:pointer;font-size:13px;color:#4ea4f6;padding:4px 8px" @click="editGrouping(g)">Edit</button>
                                    <button style="background:none;border:none;cursor:pointer;font-size:16px;color:#e74c3c;padding:4px 8px" @click="removeGrouping(g.id)">&times;</button>
                                </div>
                            </template>
                            <div style="margin-top:16px;text-align:center">
                                <button class="btn btn-primary" @click="resetForm()">+ New Grouping</button>
                            </div>
                        </div>
                    </template>
                    <!-- Form view -->
                    <template x-if="mode === 'form'">
                        <div>
                            <div class="form-group">
                                <label>Name <span style="color:#e74c3c">*</span></label>
                                <input type="text" x-model="form.name" placeholder="e.g. City Center" style="width:100%;padding:8px 10px;border:1px solid #d1d5db;border-radius:6px">
                            </div>
                            <div class="form-group">
                                <label>Description</label>
                                <input type="text" x-model="form.description" placeholder="Optional" style="width:100%;padding:8px 10px;border:1px solid #d1d5db;border-radius:6px">
                            </div>
                            <div class="form-group">
                                <label>Color</label>
                                <div style="display:flex;gap:6px;flex-wrap:wrap">
                                    <template x-for="c in palette" :key="c">
                                        <span @click="form.color = c"
                                              :style="'display:inline-block;width:28px;height:28px;border-radius:50%;cursor:pointer;background:' + c + ';border:3px solid ' + (form.color === c ? '#1a2332' : 'transparent')"
                                        ></span>
                                    </template>
                                </div>
                            </div>
                            <div class="form-group">
                                <label>Parent Grouping</label>
                                <select x-model="form.parent_id" style="width:100%;padding:8px;border:1px solid #d1d5db;border-radius:6px">
                                    <option value="">None (top-level)</option>
                                    <template x-for="g in ($store.trip.groupings || []).filter(function(g) {{ return g.id !== editId; }})" :key="g.id">
                                        <option :value="g.id" x-text="g.name"></option>
                                    </template>
                                </select>
                            </div>
                            <template x-if="editId">
                                <div class="form-group">
                                    <label>Members</label>
                                    <div style="max-height:200px;overflow-y:auto;border:1px solid #e2e5e9;border-radius:6px;padding:6px">
                                        <template x-for="a in ($store.trip.attractions || [])" :key="a.id">
                                            <label style="display:flex;align-items:center;gap:8px;padding:4px 6px;cursor:pointer;font-size:13px" @click.stop>
                                                <input type="checkbox"
                                                       :checked="(getGrouping(editId) || {{member_ids:[]}}).member_ids.includes(a.id)"
                                                       @change="$store.trip.toggleGroupingMember(editId, a.id)">
                                                <span x-text="a.name"></span>
                                            </label>
                                        </template>
                                    </div>
                                </div>
                            </template>
                            <div class="modal-actions">
                                <button class="btn btn-cancel" @click="mode = 'list'">Back</button>
                                <button class="btn btn-primary" @click="saveGrouping()" :disabled="!form.name.trim()">
                                    <span x-text="editId ? 'Save' : 'Create'"></span>
                                </button>
                            </div>
                        </div>
                    </template>
                </div>
            </div>
        </div>
    </template>

</div>

<script>
(function() {{
    var buttons = document.querySelectorAll('.nav-btn');
    var panels = document.querySelectorAll('.tab-panel');
    var saved = localStorage.getItem('vacationeer_tab') || 'tab-map';
    window.__activeTab = saved;

    function activateTab(target) {{
        window.__activeTab = target;
        localStorage.setItem('vacationeer_tab', target);
        buttons.forEach(function(b) {{ b.classList.remove('active'); }});
        panels.forEach(function(p) {{ p.classList.remove('active'); }});
        var btn = document.querySelector('.nav-btn[data-tab="' + target + '"]');
        if (btn) btn.classList.add('active');
        var panel = document.getElementById(target);
        if (panel) panel.classList.add('active');
    }}

    // Restore saved tab on load
    if (saved !== 'tab-map') activateTab(saved);

    buttons.forEach(function(btn) {{
        btn.addEventListener('click', function() {{
            activateTab(btn.getAttribute('data-tab'));
        }});
    }});
}})();
</script>
<script>
if ('serviceWorker' in navigator) {{
    navigator.serviceWorker.register('./sw.js').catch(function() {{}});
}}
</script>
</body>
</html>"""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html, encoding="utf-8")
    return output_path


def _budget_span(trip: Trip) -> str:
    if trip.budget_eur is not None:
        return f'<span>\U0001f4b6 \u20ac{trip.budget_eur:,.0f} budget</span>'
    return ""
