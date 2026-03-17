from __future__ import annotations

import json
from datetime import date, time
from pathlib import Path

from vacationeer.models.trip import Category, Trip


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
    chat_inner = tab_contents.get("chat-content", "")

    trip_json = json.dumps(
        trip.model_dump(mode="json"),
        default=_json_serializer,
        ensure_ascii=False,
    )

    category_options = "\n".join(
        f'                        <option value="{c.value}">{c.value.replace("_", " ").title()}</option>'
        for c in Category
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
<title>{_esc(trip.name)} - Vacationeer</title>
<script defer src="https://cdn.jsdelivr.net/npm/alpinejs@3.x.x/dist/cdn.min.js"></script>
<style>
*, *::before, *::after {{
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}}
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
    width: 250px;
    min-width: 250px;
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

.nav {{
    list-style: none;
    padding: 12px 0;
    flex: 1;
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

#tab-overview, #tab-timeline, #tab-chat {{
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

/* ---- fab ---- */
.fab {{
    position: fixed;
    bottom: 28px;
    right: 28px;
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

/* ---- responsive ---- */
@media (max-width: 768px) {{
    .sidebar {{
        width: 60px;
        min-width: 60px;
    }}
    .sidebar-header .brand,
    .sidebar-header .trip-name,
    .nav-btn .label,
    .sidebar-footer {{
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
    #tab-overview, #tab-timeline, #tab-chat {{
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
</script>

<script>
document.addEventListener('alpine:init', function() {{
    Alpine.store('trip', Object.assign({{}}, window.__TRIP_DATA__, {{

        async save(field, value) {{
            const resp = await fetch('/api/trip', {{
                method: 'PATCH',
                headers: {{'Content-Type': 'application/json'}},
                body: JSON.stringify({{[field]: value}})
            }});
            if (resp.ok) {{
                window.dispatchEvent(new CustomEvent('toast', {{detail: {{type: 'success', message: 'Trip updated'}}}}));
            }} else {{
                window.dispatchEvent(new CustomEvent('toast', {{detail: {{type: 'error', message: 'Failed to save'}}}}));
            }}
            return resp;
        }},

        async addAttraction(data) {{
            const resp = await fetch('/api/attractions', {{
                method: 'POST',
                headers: {{'Content-Type': 'application/json'}},
                body: JSON.stringify(data)
            }});
            if (resp.ok) {{
                const a = await resp.json();
                this.attractions.push(a);
                window.dispatchEvent(new CustomEvent('toast', {{detail: {{type: 'success', message: 'Attraction added'}}}}));
            }} else {{
                window.dispatchEvent(new CustomEvent('toast', {{detail: {{type: 'error', message: 'Failed to add attraction'}}}}));
            }}
            return resp;
        }},

        async updateAttraction(id, data) {{
            const resp = await fetch('/api/attractions/' + id, {{
                method: 'PATCH',
                headers: {{'Content-Type': 'application/json'}},
                body: JSON.stringify(data)
            }});
            if (resp.ok) {{
                const updated = await resp.json();
                const idx = this.attractions.findIndex(function(a) {{ return a.id === id; }});
                if (idx >= 0) this.attractions[idx] = updated;
                window.dispatchEvent(new CustomEvent('toast', {{detail: {{type: 'success', message: 'Attraction updated'}}}}));
            }} else {{
                window.dispatchEvent(new CustomEvent('toast', {{detail: {{type: 'error', message: 'Failed to update attraction'}}}}));
            }}
            return resp;
        }},

        async deleteAttraction(id) {{
            const resp = await fetch('/api/attractions/' + id, {{
                method: 'DELETE'
            }});
            if (resp.ok) {{
                this.attractions = this.attractions.filter(function(a) {{ return a.id !== id; }});
                window.dispatchEvent(new CustomEvent('toast', {{detail: {{type: 'success', message: 'Attraction deleted'}}}}));
            }} else {{
                window.dispatchEvent(new CustomEvent('toast', {{detail: {{type: 'error', message: 'Failed to delete attraction'}}}}));
            }}
            return resp;
        }},

        async setScore(id, score) {{
            const resp = await fetch('/api/attractions/' + id + '/score', {{
                method: 'POST',
                headers: {{'Content-Type': 'application/json'}},
                body: JSON.stringify({{score: score}})
            }});
            if (resp.ok) {{
                const idx = this.attractions.findIndex(function(a) {{ return a.id === id; }});
                if (idx >= 0) this.attractions[idx].user_score = score;
            }}
        }},

        async updatePreferences(prefs) {{
            const resp = await fetch('/api/trip/preferences', {{
                method: 'PUT',
                headers: {{'Content-Type': 'application/json'}},
                body: JSON.stringify(prefs)
            }});
            if (resp.ok) {{
                this.preferences = prefs;
                window.dispatchEvent(new CustomEvent('toast', {{detail: {{type: 'success', message: 'Preferences updated'}}}}));
            }} else {{
                window.dispatchEvent(new CustomEvent('toast', {{detail: {{type: 'error', message: 'Failed to update preferences'}}}}));
            }}
        }},

        async reload() {{
            const resp = await fetch('/api/trip');
            if (resp.ok) {{ Object.assign(this, await resp.json()); }}
        }}
    }}));
}});
</script>

<div class="app">

    <aside class="sidebar">
        <div class="sidebar-header">
            <div class="brand">Vacationeer</div>
            <div class="trip-name">{_esc(trip.destination)}</div>
        </div>
        <ul class="nav">
            <li><button class="nav-btn active" data-tab="tab-map"><span class="icon">\U0001f5fa</span><span class="label">Map</span></button></li>
            <li><button class="nav-btn" data-tab="tab-overview"><span class="icon">\U0001f4cb</span><span class="label">Overview</span></button></li>
            <li><button class="nav-btn" data-tab="tab-timeline"><span class="icon">\U0001f4c5</span><span class="label">Timeline</span></button></li>
            <li><button class="nav-btn" data-tab="tab-chat"><span class="icon">\U0001f4ac</span><span class="label">Chat</span></button></li>
        </ul>
        <div class="sidebar-footer">Vacationeer v0.1</div>
    </aside>

    <div class="main">
        <header class="header">
            <div class="header-title-row" onclick="window.dispatchEvent(new CustomEvent('open-modal', {{detail: 'edit-trip'}}))">
                <h1>{_esc(trip.name)}</h1>
                <span class="edit-icon">\u270f\ufe0f</span>
            </div>
            <div class="meta" style="cursor:pointer" onclick="window.dispatchEvent(new CustomEvent('open-modal', {{detail: 'edit-trip'}}))">
                <span>\U0001f4cd {_esc(trip.destination)}</span>
                <span>\U0001f4c6 {start} &ndash; {end} ({num_days} days)</span>
                <span>\U0001f465 {trip.travelers} travelers</span>
                {_budget_span(trip)}
            </div>
        </header>
        <div class="content">
            <div id="tab-map" class="tab-panel active">
                <iframe src="{_esc(map_filename)}"></iframe>
            </div>
            <div id="tab-overview" class="tab-panel">
                <div id="overview-content">{overview_inner if overview_inner else '<div class="tab-placeholder">Overview will appear here.</div>'}</div>
            </div>
            <div id="tab-timeline" class="tab-panel">
                <div id="timeline-content">{timeline_inner if timeline_inner else '<div class="tab-placeholder">Timeline will appear here.</div>'}</div>
            </div>
            <div id="tab-chat" class="tab-panel">
                <div id="chat-content">{chat_inner if chat_inner else '<div class="tab-placeholder">Chat will appear here.</div>'}</div>
            </div>
        </div>
    </div>

</div>

<!-- Floating add button -->
<button class="fab" onclick="window.dispatchEvent(new CustomEvent('open-modal', {{detail: 'add-attraction'}}))" title="Add attraction">+</button>

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
        <div class="modal-backdrop" @click.self="modal = null">
            <div class="modal" x-data="{{
                form: {{ name: '', description: '', category: 'landmark', lat: '', lng: '', address: '', price_eur: '', duration_minutes: '', tags: '', tips: '', url: '' }},
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
                        tags: this.form.tags ? this.form.tags.split(',').map(function(t) {{ return t.trim(); }}).filter(Boolean) : [],
                        tips: this.form.tips.trim() || null,
                        url: this.form.url.trim() || null
                    }};
                    const resp = await $store.trip.addAttraction(data);
                    if (resp.ok) window.dispatchEvent(new CustomEvent('close-modal'));
                }}
            }}">
                <div class="modal-header">Add Attraction</div>
                <div class="modal-body">
                    <div class="form-group">
                        <label>Name *</label>
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
                    <div class="form-row">
                        <div class="form-group">
                            <label>Latitude</label>
                            <input type="number" step="any" x-model="form.lat" placeholder="39.4699">
                        </div>
                        <div class="form-group">
                            <label>Longitude</label>
                            <input type="number" step="any" x-model="form.lng" placeholder="-0.3763">
                        </div>
                    </div>
                    <div class="form-group">
                        <label>Address</label>
                        <input type="text" x-model="form.address" placeholder="Street address">
                    </div>
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
                        <label>Tags (comma-separated)</label>
                        <input type="text" x-model="form.tags" placeholder="beach, sunset, free">
                    </div>
                    <div class="form-group">
                        <label>Tips</label>
                        <textarea x-model="form.tips" placeholder="Travel tips or notes"></textarea>
                    </div>
                    <div class="form-group">
                        <label>URL</label>
                        <input type="url" x-model="form.url" placeholder="https://...">
                    </div>
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
        <div class="modal-backdrop" @click.self="modal = null">
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
                        <label>Trip Name</label>
                        <input type="text" x-model="form.name">
                    </div>
                    <div class="form-group">
                        <label>Destination</label>
                        <input type="text" x-model="form.destination">
                    </div>
                    <div class="form-row">
                        <div class="form-group">
                            <label>Start Date</label>
                            <input type="date" x-model="form.start_date">
                        </div>
                        <div class="form-group">
                            <label>End Date</label>
                            <input type="date" x-model="form.end_date">
                        </div>
                    </div>
                    <div class="form-row">
                        <div class="form-group">
                            <label>Travelers</label>
                            <input type="number" min="1" x-model="form.travelers">
                        </div>
                        <div class="form-group">
                            <label>Total Budget (&euro;)</label>
                            <input type="number" step="0.01" x-model="form.budget_eur" placeholder="Optional">
                        </div>
                    </div>
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
        <div class="modal-backdrop" @click.self="modal = null">
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

</div>

<script>
(function() {{
    var buttons = document.querySelectorAll('.nav-btn');
    var panels = document.querySelectorAll('.tab-panel');

    buttons.forEach(function(btn) {{
        btn.addEventListener('click', function() {{
            var target = btn.getAttribute('data-tab');
            buttons.forEach(function(b) {{ b.classList.remove('active'); }});
            panels.forEach(function(p) {{ p.classList.remove('active'); }});
            btn.classList.add('active');
            document.getElementById(target).classList.add('active');
        }});
    }});
}})();
</script>
</body>
</html>"""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html, encoding="utf-8")
    return output_path


def _esc(text: str) -> str:
    """Minimal HTML escaping."""
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _budget_span(trip: Trip) -> str:
    if trip.budget_eur is not None:
        return f'<span>\U0001f4b6 \u20ac{trip.budget_eur:,.0f} budget</span>'
    return ""
