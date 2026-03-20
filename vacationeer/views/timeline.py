from __future__ import annotations

from vacationeer.models.trip import Trip
from vacationeer.theme import BG_LIGHT, BG_WHITE, BORDER, BORDER_LIGHT, CATEGORY_META, PRIMARY, TEXT_MUTED


def render_timeline(trip: Trip) -> str:
    """Return HTML string for the Kanban-style timeline tab."""

    # Build category color map for JS
    cat_colors_js = ", ".join(
        f"'{cat.value}': '{info.color}'"
        for cat, info in CATEGORY_META.items()
    )

    # NOTE: This is an f-string. JS/CSS braces need {{ }} escaping.
    return f"""
<style>
.kanban {{
    display: flex;
    height: calc(100vh - 200px);
    min-height: 500px;
    overflow: hidden;
    font-family: system-ui, -apple-system, sans-serif;
}}
.kanban-pool {{
    width: 260px;
    min-width: 260px;
    border-right: 1px solid {BORDER};
    overflow-y: auto;
    padding: 12px;
    background: {BG_LIGHT};
    flex-shrink: 0;
}}
.kanban-pool-header {{
    font-size: 14px;
    font-weight: 700;
    color: {PRIMARY};
    margin-bottom: 10px;
    display: flex;
    align-items: center;
    justify-content: space-between;
}}
.kanban-days {{
    flex: 1;
    overflow-x: auto;
    overflow-y: hidden;
}}
.kanban-days-scroll {{
    display: flex;
    gap: 12px;
    padding: 12px;
    height: 100%;
    min-width: min-content;
}}
.day-col {{
    width: 280px;
    min-width: 280px;
    background: {BG_WHITE};
    border-radius: 12px;
    border: 1px solid {BORDER};
    display: flex;
    flex-direction: column;
    max-height: 100%;
}}
.day-col-header {{
    padding: 10px 14px;
    border-bottom: 1px solid {BORDER_LIGHT};
    flex-shrink: 0;
}}
.day-col-title {{
    display: flex;
    align-items: center;
    justify-content: space-between;
}}
.day-num {{
    font-size: 13px;
    font-weight: 700;
    color: {PRIMARY};
}}
.day-date {{
    font-size: 11px;
    color: {TEXT_MUTED};
    margin-left: 6px;
}}
.day-col-label {{
    font-size: 12px;
    color: #555;
    margin-top: 2px;
    cursor: pointer;
}}
.day-col-label:hover {{
    color: {PRIMARY};
}}
.day-col-notes {{
    font-size: 11px;
    color: {TEXT_MUTED};
    padding: 4px 14px;
    border-bottom: 1px solid {BORDER_LIGHT};
    cursor: pointer;
}}
.day-col-notes:hover {{
    color: #555;
}}
.day-col-actions {{
    display: flex;
    gap: 4px;
}}
.day-col-actions button {{
    background: none;
    border: 1px solid {BORDER};
    border-radius: 4px;
    cursor: pointer;
    font-size: 14px;
    width: 28px;
    height: 28px;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 0;
    color: {TEXT_MUTED};
}}
.day-col-actions button:hover {{
    background: {BG_LIGHT};
    color: {PRIMARY};
}}
.day-col-list {{
    flex: 1;
    overflow-y: auto;
    padding: 8px;
    min-height: 60px;
}}
.day-col-footer {{
    padding: 8px 14px;
    border-top: 1px solid {BORDER_LIGHT};
    font-size: 11px;
    color: {TEXT_MUTED};
    display: flex;
    gap: 12px;
    flex-shrink: 0;
}}
.day-col-empty {{
    padding: 24px;
    text-align: center;
    color: {TEXT_MUTED};
    border: 2px dashed {BORDER};
    border-radius: 8px;
    margin: 4px;
    font-size: 13px;
}}
/* Pool cards */
.pool-card {{
    padding: 8px 10px;
    margin-bottom: 6px;
    background: white;
    border-radius: 8px;
    border-left: 3px solid;
    cursor: grab;
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 12px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.06);
    transition: box-shadow 0.15s;
    user-select: none;
    -webkit-user-select: none;
}}
.pool-card:hover {{
    box-shadow: 0 2px 6px rgba(0,0,0,0.12);
}}
.pool-card .card-name {{
    font-weight: 600;
    font-size: 13px;
    color: {PRIMARY};
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}}
.pool-card .card-desc, .act-card .card-desc {{
    font-size: 11px;
    color: #888;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    margin-top: 1px;
}}
.pool-card .card-meta {{
    font-size: 11px;
    color: {TEXT_MUTED};
}}
/* Activity cards in day columns */
.act-card {{
    padding: 8px 10px;
    margin-bottom: 6px;
    background: #f8f9fa;
    border-radius: 8px;
    border-left: 3px solid;
    cursor: grab;
    display: flex;
    align-items: flex-start;
    gap: 8px;
    font-size: 12px;
    transition: box-shadow 0.15s;
    user-select: none;
    -webkit-user-select: none;
}}
.act-card:hover {{
    box-shadow: 0 2px 6px rgba(0,0,0,0.1);
}}
.act-card .card-time {{
    font-size: 11px;
    font-weight: 600;
    color: {PRIMARY};
    min-width: 36px;
}}
.act-card .card-name {{
    font-weight: 600;
    font-size: 13px;
    color: {PRIMARY};
}}
.act-card .card-meta {{
    font-size: 11px;
    color: {TEXT_MUTED};
}}
.card-buttons {{
    display: flex;
    flex-direction: column;
    gap: 2px;
    margin-left: auto;
    flex-shrink: 0;
}}
.card-btn {{
    background: none;
    border: 1px solid {BORDER};
    border-radius: 4px;
    cursor: pointer;
    color: #aaa;
    font-size: 14px;
    width: 28px;
    height: 28px;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 0;
}}
.card-btn:hover {{
    background: {BG_LIGHT};
    color: {PRIMARY};
}}
.card-btn.btn-remove:hover {{
    background: #fef2f2;
    color: #e74c3c;
    border-color: #e74c3c;
}}
/* Pool card expand */
.pool-card .card-btn {{
    margin-left: auto;
    flex-shrink: 0;
}}
/* Inline edit */
.day-edit-input {{
    width: 100%;
    padding: 4px 8px;
    border: 1px solid {BORDER};
    border-radius: 4px;
    font-size: 12px;
    font-family: inherit;
    outline: none;
}}
.day-edit-input:focus {{
    border-color: {PRIMARY};
}}
/* Time gap markers */
.time-gap {{
    text-align: center;
    font-size: 10px;
    color: {TEXT_MUTED};
    padding: 2px 0;
    opacity: 0.7;
}}
/* SortableJS ghost */
.sortable-ghost {{
    opacity: 0.4;
}}
/* Mobile — tablet */
@media (max-width: 768px) {{
    .kanban {{
        flex-direction: column;
        height: auto;
        min-height: 0;
    }}
    .kanban-pool {{
        width: 100%;
        min-width: 100%;
        max-height: 200px;
        border-right: none;
        border-bottom: 1px solid {BORDER};
    }}
    .kanban-days-scroll {{
        flex-direction: column;
        padding: 8px;
        gap: 8px;
    }}
    .day-col {{
        width: 100%;
        min-width: 100%;
        max-height: none;
    }}
    /* Bigger touch targets on mobile */
    .card-btn, .day-col-actions button {{
        width: 36px;
        height: 36px;
        font-size: 16px;
    }}
    .pool-card, .act-card {{
        padding: 10px 12px;
        gap: 10px;
    }}
    .pool-card .card-name, .act-card .card-name {{
        font-size: 14px;
    }}
    /* Itinerary bar: scroll on mobile */
    .itin-bar {{
        flex-wrap: nowrap;
        overflow-x: auto;
        -webkit-overflow-scrolling: touch;
        padding: 8px 8px;
        gap: 4px;
    }}
    .itin-tab {{
        padding: 7px 14px;
        font-size: 13px;
        min-height: 36px;
    }}
    .compare-btn {{
        padding: 7px 12px;
        font-size: 12px;
        min-height: 36px;
        white-space: nowrap;
    }}
    .itin-add {{
        white-space: nowrap;
    }}
    /* Compare panel */
    .compare-panel {{
        height: auto;
        max-height: calc(100vh - 200px);
    }}
    .compare-table {{
        font-size: 12px;
    }}
    .compare-table th, .compare-table td {{
        padding: 6px 8px;
    }}
    /* New itinerary form responsive */
    .new-itin-form {{
        flex-wrap: wrap;
    }}
    .new-itin-form input, .new-itin-form select {{
        min-width: 0;
        flex: 1 1 100%;
    }}
}}
/* Mobile — small phone */
@media (max-width: 480px) {{
    .kanban-pool {{
        max-height: 160px;
        padding: 8px;
    }}
    .kanban-days-scroll {{
        padding: 6px;
        gap: 6px;
    }}
    .day-col-header {{
        padding: 8px 10px;
    }}
    .day-col-list {{
        padding: 6px;
    }}
    .itin-bar {{
        padding: 6px;
    }}
    .itin-tab {{
        padding: 6px 10px;
        font-size: 12px;
    }}
}}
.itin-bar {{
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 8px 12px;
    background: {BG_WHITE};
    border-bottom: 1px solid {BORDER};
    flex-shrink: 0;
}}
.itin-tabs {{
    display: flex;
    gap: 4px;
    flex: 1;
    overflow-x: auto;
}}
.itin-tab {{
    padding: 5px 14px;
    border-radius: 20px;
    border: 1px solid {BORDER};
    background: {BG_WHITE};
    cursor: pointer;
    font-size: 12px;
    font-weight: 500;
    color: #555;
    white-space: nowrap;
    transition: all 0.15s;
    display: flex;
    align-items: center;
    gap: 6px;
}}
.itin-tab:hover {{
    border-color: {PRIMARY};
    color: {PRIMARY};
}}
.itin-tab.active {{
    background: {PRIMARY};
    color: #fff;
    border-color: {PRIMARY};
}}
.itin-tab .itin-badge {{
    font-size: 10px;
    opacity: 0.7;
}}
.itin-tab.active .itin-badge {{
    opacity: 0.85;
}}
.itin-dots {{
    margin-left: 2px;
    padding: 0 4px;
    border-radius: 4px;
    font-size: 14px;
    line-height: 1;
    opacity: 0.5;
    cursor: pointer;
}}
.itin-dots:hover {{
    opacity: 1;
    background: rgba(0,0,0,0.1);
}}
.itin-tab.active .itin-dots:hover {{
    background: rgba(255,255,255,0.2);
}}
.itin-add {{
    border-style: dashed;
    color: {TEXT_MUTED};
}}
.itin-add:hover {{
    border-color: {PRIMARY};
    color: {PRIMARY};
}}
.itin-actions {{
    position: relative;
    display: inline-block;
}}
.itin-menu {{
    position: absolute;
    top: 100%;
    right: 0;
    margin-top: 4px;
    background: #fff;
    border: 1px solid {BORDER};
    border-radius: 8px;
    box-shadow: 0 4px 12px rgba(0,0,0,0.12);
    z-index: 50;
    min-width: 140px;
    padding: 4px 0;
}}
.itin-menu button {{
    display: block;
    width: 100%;
    text-align: left;
    padding: 6px 14px;
    border: none;
    background: none;
    cursor: pointer;
    font-size: 12px;
    color: #333;
}}
.itin-menu button:hover {{
    background: {BG_LIGHT};
}}
.itin-menu button.danger {{
    color: #e74c3c;
}}
.compare-btn {{
    padding: 5px 12px;
    border-radius: 20px;
    border: 1px solid {BORDER};
    background: {BG_WHITE};
    cursor: pointer;
    font-size: 11px;
    font-weight: 500;
    color: #555;
    transition: all 0.15s;
}}
.compare-btn:hover {{
    border-color: {PRIMARY};
    color: {PRIMARY};
}}
.compare-btn.active {{
    background: #1a2332;
    color: #fff;
    border-color: #1a2332;
}}
.compare-panel {{
    padding: 16px;
    overflow: auto;
    height: calc(100vh - 250px);
}}
.compare-table {{
    width: 100%;
    border-collapse: collapse;
    font-size: 13px;
}}
.compare-table th, .compare-table td {{
    padding: 8px 12px;
    border: 1px solid {BORDER_LIGHT};
    text-align: left;
}}
.compare-table th {{
    background: {BG_LIGHT};
    font-weight: 600;
    font-size: 12px;
    color: #555;
}}
.compare-table td {{
    vertical-align: top;
}}
.compare-grid {{
    margin-top: 16px;
}}
.compare-grid-header {{
    display: grid;
    gap: 1px;
    background: {BORDER_LIGHT};
    border-radius: 8px 8px 0 0;
    overflow: hidden;
    font-size: 12px;
    font-weight: 600;
    color: #555;
}}
.compare-grid-header > div {{
    background: {BG_LIGHT};
    padding: 6px 10px;
}}
.compare-grid-row {{
    display: grid;
    gap: 1px;
    background: {BORDER_LIGHT};
}}
.compare-grid-row > div {{
    background: {BG_WHITE};
    padding: 6px 10px;
    min-height: 40px;
}}
.compare-pill {{
    display: inline-block;
    padding: 2px 8px;
    border-radius: 10px;
    font-size: 10px;
    margin: 1px;
    white-space: nowrap;
}}
.new-itin-form {{
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 4px 0;
}}
.new-itin-form input, .new-itin-form select {{
    padding: 4px 8px;
    border: 1px solid {BORDER};
    border-radius: 6px;
    font-size: 12px;
}}
.new-itin-form button {{
    padding: 4px 10px;
    border-radius: 6px;
    border: none;
    cursor: pointer;
    font-size: 12px;
}}
</style>

<div x-data="{{
    showCompare: false,
    showNewItin: false,
    newItinName: '',
    newItinDesc: '',
    newItinClone: '',
    menuOpen: null,
    editing: null,
    editName: '',
    editDesc: '',
    catColors: {{{cat_colors_js}}},

    itinStats(itin) {{
        var total = ($store.trip.attractions || []).length + ($store.trip.day_trips || []).length;
        var scheduled = 0;
        var hours = 0;
        var cost = 0;
        var busiestDay = '';
        var busiestHrs = 0;
        (itin.days || []).forEach(function(d) {{
            var dayMins = 0;
            (d.activities || []).forEach(function(a) {{
                scheduled++;
                hours += (a.duration_minutes || 0);
                cost += (a.price_eur || 0);
                dayMins += (a.duration_minutes || 0);
            }});
            var dayH = dayMins / 60;
            if (dayH > busiestHrs) {{ busiestHrs = dayH; busiestDay = d.date; }}
        }});
        return {{ total: total, scheduled: scheduled, hours: (hours/60).toFixed(1), cost: cost.toFixed(0), busiestDay: busiestDay, busiestHrs: busiestHrs.toFixed(1) }};
    }},

    async submitNewItin() {{
        if (!this.newItinName.trim()) return;
        await $store.trip.createItinerary(this.newItinName.trim(), this.newItinClone || null, this.newItinDesc.trim() || null);
        this.showNewItin = false;
        this.newItinName = '';
        this.newItinDesc = '';
        this.newItinClone = '';
    }},

    startEdit(itin) {{
        this.editing = itin.id;
        this.editName = itin.name;
        this.editDesc = itin.description || '';
        this.menuOpen = null;
    }},

    async submitEdit() {{
        if (!this.editName.trim() || !this.editing) return;
        await $store.trip.updateItinerary(this.editing, {{
            name: this.editName.trim(),
            description: this.editDesc.trim() || null
        }});
        this.editing = null;
    }},

    defaultNewName() {{
        var letters = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ';
        var n = ($store.trip.itineraries || []).length;
        return 'Itinerary ' + (letters[n] || String(n + 1));
    }}
}}"
>

<!-- Itinerary switcher bar -->
<div class="itin-bar" x-show="($store.trip.itineraries || []).length > 0">
    <div class="itin-tabs">
        <template x-for="itin in ($store.trip.itineraries || [])" :key="itin.id">
            <div class="itin-actions">
                <button class="itin-tab"
                        :class="itin.id === $store.trip.active_itinerary_id ? 'active' : ''"
                        @click="$store.trip.switchItinerary(itin.id)">
                    <span x-text="itin.name"></span>
                    <span class="itin-badge" x-text="'(' + itinStats(itin).scheduled + '/' + itinStats(itin).total + ')'"></span>
                    <span class="itin-dots" @click.stop="menuOpen = menuOpen === itin.id ? null : itin.id"
                          title="Options">&#x22EF;</span>
                </button>
                <!-- Dropdown menu -->
                <div class="itin-menu" x-show="menuOpen === itin.id" @click.away="menuOpen = null" x-cloak>
                    <button @click="startEdit(itin)">Edit</button>
                    <button @click="$store.trip.cloneItinerary(itin.id); menuOpen = null;">Duplicate</button>
                    <button class="danger" @click="if(confirm('Delete \\'' + itin.name + '\\'?')) {{ $store.trip.deleteItinerary(itin.id); }} menuOpen = null;"
                            x-show="($store.trip.itineraries || []).length > 1">Delete</button>
                </div>
            </div>
        </template>
        <button class="itin-tab itin-add" @click="showNewItin = !showNewItin; newItinName = defaultNewName(); newItinClone = '';">+ New</button>
    </div>
    <button class="compare-btn" :class="showCompare ? 'active' : ''"
            @click="showCompare = !showCompare"
            x-show="($store.trip.itineraries || []).length > 1">\u2194 Compare</button>
</div>

<!-- Active itinerary description -->
<template x-for="itin in ($store.trip.itineraries || []).filter(i => i.id === $store.trip.active_itinerary_id && i.description)" :key="itin.id + '-desc'">
    <div style="padding:4px 16px;font-size:11px;color:{TEXT_MUTED};background:{BG_LIGHT};border-bottom:1px solid {BORDER_LIGHT};"
         @click="startEdit(itin)" title="Click to edit">
        <span x-text="itin.description"></span>
    </div>
</template>

<!-- Edit itinerary inline -->
<div class="itin-bar" x-show="editing" style="background:#fffbeb;border-bottom-color:#f59e0b;flex-wrap:wrap;gap:6px;" x-cloak>
    <div style="display:flex;align-items:center;gap:6px;flex:1;min-width:200px;">
        <label style="font-size:11px;color:#92400e;font-weight:600;">Name</label>
        <input x-model="editName" @keydown.enter="submitEdit()" @keydown.escape="editing=null"
               style="padding:4px 8px;border:1px solid #d1d5db;border-radius:6px;font-size:12px;flex:1;max-width:200px;"
               x-ref="editNameInput" x-effect="if(editing) $nextTick(() => $refs.editNameInput && $refs.editNameInput.focus())">
    </div>
    <div style="display:flex;align-items:center;gap:6px;flex:2;min-width:200px;">
        <label style="font-size:11px;color:#92400e;font-weight:600;">Description</label>
        <input x-model="editDesc" @keydown.enter="submitEdit()" @keydown.escape="editing=null"
               placeholder="Optional description..."
               style="padding:4px 8px;border:1px solid #d1d5db;border-radius:6px;font-size:12px;flex:1;">
    </div>
    <div style="display:flex;gap:4px;">
        <button @click="submitEdit()" style="padding:4px 10px;border-radius:6px;border:none;background:{PRIMARY};color:#fff;cursor:pointer;font-size:12px;">Save</button>
        <button @click="editing=null" style="padding:4px 10px;border-radius:6px;border:none;background:#e5e7eb;color:#374151;cursor:pointer;font-size:12px;">Cancel</button>
    </div>
</div>

<!-- New itinerary form -->
<div class="itin-bar" x-show="showNewItin" style="background:#f0f9ff;border-bottom-color:{PRIMARY};" x-cloak>
    <div class="new-itin-form" style="flex-wrap:wrap;">
        <input x-model="newItinName" placeholder="Name..." @keydown.escape="showNewItin=false"
               x-ref="newItinInput" x-effect="if(showNewItin) $nextTick(() => $refs.newItinInput && $refs.newItinInput.focus())"
               style="width:150px;">
        <input x-model="newItinDesc" placeholder="Description (optional)..." @keydown.escape="showNewItin=false"
               style="width:200px;">
        <select x-model="newItinClone">
            <option value="">Start empty</option>
            <template x-for="it in ($store.trip.itineraries || [])" :key="it.id">
                <option :value="it.id" x-text="'Clone ' + it.name"></option>
            </template>
        </select>
        <button @click="submitNewItin()" style="background:{PRIMARY};color:#fff;">Create</button>
        <button @click="showNewItin=false" style="background:#e5e7eb;color:#374151;">Cancel</button>
    </div>
</div>

<!-- Comparison panel -->
<div class="compare-panel" x-show="showCompare" x-cloak>
    <table class="compare-table">
        <thead>
            <tr>
                <th>Metric</th>
                <template x-for="itin in ($store.trip.itineraries || [])" :key="itin.id">
                    <th x-text="itin.name"></th>
                </template>
            </tr>
        </thead>
        <tbody>
            <tr>
                <td>Scheduled</td>
                <template x-for="itin in ($store.trip.itineraries || [])" :key="itin.id + '-sched'">
                    <td>
                        <span x-text="itinStats(itin).scheduled + ' / ' + itinStats(itin).total"></span>
                        <span style="color:#999;font-size:11px;" x-text="'(' + (itinStats(itin).total ? Math.round(itinStats(itin).scheduled / itinStats(itin).total * 100) : 0) + '%)'"></span>
                    </td>
                </template>
            </tr>
            <tr>
                <td>Total hours</td>
                <template x-for="itin in ($store.trip.itineraries || [])" :key="itin.id + '-hrs'">
                    <td x-text="itinStats(itin).hours + 'h'"></td>
                </template>
            </tr>
            <tr>
                <td>Total cost</td>
                <template x-for="itin in ($store.trip.itineraries || [])" :key="itin.id + '-cost'">
                    <td x-text="'\\u20ac' + itinStats(itin).cost"></td>
                </template>
            </tr>
            <tr>
                <td>Busiest day</td>
                <template x-for="itin in ($store.trip.itineraries || [])" :key="itin.id + '-busy'">
                    <td x-text="itinStats(itin).busiestDay ? (itinStats(itin).busiestDay + ' (' + itinStats(itin).busiestHrs + 'h)') : '-'"></td>
                </template>
            </tr>
        </tbody>
    </table>

    <!-- Day-by-day grid -->
    <div class="compare-grid" x-show="($store.trip.itineraries || []).length > 1">
        <h4 style="margin:16px 0 8px;font-size:13px;color:#555;">Day-by-day comparison</h4>
        <div class="compare-grid-header" :style="'grid-template-columns: 100px repeat(' + ($store.trip.itineraries || []).length + ', 1fr)'">
            <div>Day</div>
            <template x-for="itin in ($store.trip.itineraries || [])" :key="itin.id + '-gh'">
                <div x-text="itin.name"></div>
            </template>
        </div>
        <template x-for="dayDate in (function() {{
            var dates = new Set();
            ($store.trip.itineraries || []).forEach(function(it) {{
                (it.days || []).forEach(function(d) {{ dates.add(d.date); }});
            }});
            return Array.from(dates).sort();
        }})()" :key="dayDate">
            <div class="compare-grid-row" :style="'grid-template-columns: 100px repeat(' + ($store.trip.itineraries || []).length + ', 1fr)'">
                <div style="font-size:11px;font-weight:600;color:#555;">
                    <span x-text="dayDate"></span>
                </div>
                <template x-for="itin in ($store.trip.itineraries || [])" :key="itin.id + '-' + dayDate">
                    <div>
                        <template x-for="act in (function() {{
                            var day = (itin.days || []).find(function(d) {{ return d.date === dayDate; }});
                            return day ? (day.activities || []) : [];
                        }})()" :key="act.id">
                            <span class="compare-pill"
                                  :style="'background:' + (catColors[act.category] || '#999') + '22;color:' + (catColors[act.category] || '#999') + ';border:1px solid ' + (catColors[act.category] || '#999') + '44'"
                                  x-text="act.name.length > 20 ? act.name.substring(0,18) + '...' : act.name"></span>
                        </template>
                        <template x-if="!(function() {{
                            var day = (itin.days || []).find(function(d) {{ return d.date === dayDate; }});
                            return day && day.activities && day.activities.length > 0;
                        }})()">
                            <span style="color:#ccc;font-size:11px;">-</span>
                        </template>
                    </div>
                </template>
            </div>
        </template>
    </div>
</div>

<div class="kanban" x-data="kanbanTimeline()" x-init="
    var self = this;
    setTimeout(function() {{ self.initAllSortables(); }}, 200);
    $watch('$store.trip.active_itinerary_id', function() {{
        self.$nextTick(function() {{ setTimeout(function() {{ self.initAllSortables(); }}, 100); }});
    }});
">

  <!-- Left sidebar: unscheduled pool -->
  <aside class="kanban-pool">
    <div class="kanban-pool-header">
      <span>Unscheduled (<span x-text="unscheduled.length">0</span>)</span>
    </div>
    <div x-ref="poolList">
      <template x-for="attr in unscheduled" :key="attr.id">
        <div class="pool-card" :data-attraction-id="attr.id"
             :style="'border-left-color:' + catColor(attr.category)">
          <div style="flex:1;min-width:0;">
            <div class="card-name"><span x-show="attr.visited" style="color:#27ae60;margin-right:4px" title="Visited">&#x2705;</span><span x-text="attr.name"></span></div>
            <div class="card-desc" x-show="attr.description" x-text="attr.description"></div>
            <div class="card-meta">
              <span x-show="attr.duration_minutes" x-text="fmtDuration(attr.duration_minutes)"></span>
              <span x-show="attr.price_eur != null" x-text="fmtPrice(attr.price_eur)"></span>
              <span x-show="attr.expected_score" :style="'color:' + (attr.expected_score >= 8 ? '#27AE60' : attr.expected_score >= 6 ? '#F1C40F' : '#E74C3C')"
                    x-text="'\\u2605' + (attr.expected_score||0).toFixed(1)"></span>
            </div>
            <div style="display:flex;flex-wrap:wrap;gap:2px;">
              <template x-for="g in ($store.trip.groupings || []).filter(g => g.member_ids.includes(attr.id))" :key="g.id">
                <span :style="'display:inline-block;padding:0 5px;border-radius:8px;font-size:9px;color:#fff;background:' + g.color + ';margin-right:3px;margin-top:2px;'" x-text="g.name"></span>
              </template>
            </div>
          </div>
          <a class="card-btn" :href="googleMapsUrl(attr.location, attr.name)" target="_blank" rel="noopener" @click.stop title="Google Maps" style="text-decoration:none;color:inherit;">&#x1f4cd;</a>
          <button class="card-btn" @click.stop="window.dispatchEvent(new CustomEvent('open-attraction', {{detail: {{id: attr.id}}}}))" title="Details">&#x25BC;</button>
        </div>
      </template>
      <!-- Day trips -->
      <template x-for="dt in unscheduledDayTrips" :key="dt.id">
        <div class="pool-card" :data-daytrip-id="dt.id"
             style="border-left-color:#1E8449;">
          <div style="flex:1;min-width:0;">
            <div class="card-name"><span x-show="dt.visited" style="color:#27ae60;margin-right:4px" title="Visited">&#x2705;</span><span x-text="dt.name"></span></div>
            <div class="card-desc" x-show="dt.description" x-text="dt.description"></div>
            <div class="card-meta" style="color:#1E8449;">Day Trip</div>
            <div style="display:flex;flex-wrap:wrap;gap:2px;">
              <template x-for="g in ($store.trip.groupings || []).filter(g => g.member_ids.includes(dt.id))" :key="g.id">
                <span :style="'display:inline-block;padding:0 5px;border-radius:8px;font-size:9px;color:#fff;background:' + g.color + ';margin-right:3px;margin-top:2px;'" x-text="g.name"></span>
              </template>
            </div>
          </div>
          <button class="card-btn" @click.stop="window.dispatchEvent(new CustomEvent('open-attraction', {{detail: {{id: dt.id}}}}))" title="Details">&#x25BC;</button>
        </div>
      </template>
      <div x-show="!unscheduled.length && !unscheduledDayTrips.length"
           style="text-align:center;padding:20px;color:{TEXT_MUTED};font-size:13px;">
        All scheduled!
      </div>
    </div>
  </aside>

  <!-- Day columns -->
  <main class="kanban-days">
    <div class="kanban-days-scroll" x-ref="daysScroll">
      <template x-for="(day, i) in days" :key="day.date">
        <div class="day-col" :data-day-date="day.date">

          <!-- Column header -->
          <div class="day-col-header">
            <div class="day-col-title">
              <div>
                <span class="day-num">Day <span x-text="i+1"></span> &mdash; <span x-text="dayName(day.date)"></span></span>
                <span class="day-date" x-text="shortDate(day.date)"></span>
                <template x-if="!editing || editing.date !== day.date || editing.field !== 'label'">
                  <span class="day-col-label"
                        x-show="day.label"
                        x-text="day.label"
                        @click.stop="startEdit(day, 'label')"></span>
                </template>
                <template x-if="editing && editing.date === day.date && editing.field === 'label'">
                  <input class="day-edit-input" type="text"
                         x-model="editing.value"
                         @keydown.enter="saveEdit()"
                         @keydown.escape="cancelEdit()"
                         @blur="saveEdit()"
                         x-ref="editInput">
                </template>
              </div>
              <div class="day-col-actions">
                <button x-show="i > 0" @click="swapDays(days[i-1].date, day.date)"
                        title="Move left">&larr;</button>
                <button x-show="i < days.length - 1" @click="swapDays(day.date, days[i+1].date)"
                        title="Move right">&rarr;</button>
              </div>
            </div>
          </div>

          <!-- Notes -->
          <template x-if="!editing || editing.date !== day.date || editing.field !== 'notes'">
            <div class="day-col-notes"
                 x-show="day.notes || true"
                 x-text="day.notes || 'Click to add notes...'"
                 :style="!day.notes ? 'font-style:italic;opacity:0.5;' : ''"
                 @click.stop="startEdit(day, 'notes')"></div>
          </template>
          <template x-if="editing && editing.date === day.date && editing.field === 'notes'">
            <div style="padding:4px 14px;border-bottom:1px solid {BORDER_LIGHT};">
              <input class="day-edit-input" type="text"
                     x-model="editing.value"
                     placeholder="Day notes..."
                     @keydown.enter="saveEdit()"
                     @keydown.escape="cancelEdit()"
                     @blur="saveEdit()"
                     x-ref="editInput">
            </div>
          </template>

          <!-- Activities list (SortableJS target) -->
          <div class="day-col-list" :data-day-list="day.date">
            <template x-for="act in sortedActivities(day)" :key="act.id">
              <div class="act-card"
                   :data-activity-id="act.id"
                   :data-attraction-id="act.attraction_id || ''"
                   :style="'border-left-color:' + catColor(act.category) + ';min-height:' + Math.max(Math.round((act.duration_minutes || 30) * 0.5), 28) + 'px'">
                <div style="flex:1;min-width:0;">
                  <div style="display:flex;align-items:center;gap:6px;">
                    <span class="card-time" x-show="act.start_time" x-text="act.start_time || ''"></span>
                    <span class="card-name" x-text="act.name"></span>
                  </div>
                  <div class="card-desc" x-show="actDescription(act)" x-text="actDescription(act)"></div>
                  <div class="card-meta">
                    <span x-show="act.duration_minutes" x-text="fmtDuration(act.duration_minutes)"></span>
                    <span x-show="act.notes" x-text="act.notes" style="color:#888;font-style:italic;"></span>
                  </div>
                </div>
                <div class="card-buttons">
                  <button class="card-btn btn-remove" @click.stop="unscheduleItem(day.date, act.id)"
                          title="Remove">&times;</button>
                  <button class="card-btn" @click.stop="window.dispatchEvent(new CustomEvent('open-attraction', {{detail: {{id: act.attraction_id || act.day_trip_id, dayDate: day.date, activityId: act.id}}}}))"
                          title="Details">&#x25BC;</button>
                </div>
              </div>
            </template>
            <div class="day-col-empty" x-show="!day.activities || !day.activities.length">
              Drop activities here
            </div>
          </div>

          <!-- Footer stats -->
          <div class="day-col-footer">
            <span x-text="dayStats(day).hours + 'h'"></span>
            <span x-text="'\\u20ac' + dayStats(day).cost"></span>
            <span x-text="(day.activities || []).length + ' items'"></span>
          </div>
        </div>
      </template>
    </div>
  </main>


</div>

</div> <!-- end outer itinerary wrapper -->

<script>
function kanbanTimeline() {{
    return {{
        _sortables: [],
        _dragging: false,
        editing: null,
        catColors: {{{cat_colors_js}}},
        catLabels: {{
            'landmark': 'Landmark', 'museum': 'Museum', 'nature': 'Nature',
            'food': 'Food & Drink', 'entertainment': 'Entertainment',
            'transport': 'Transport', 'accommodation': 'Accommodation',
            'shopping': 'Shopping', 'day_trip': 'Day Trip', 'infrastructure': 'Infrastructure'
        }},

        catColor: function(c) {{ return this.catColors[c] || '#999'; }},

        get days() {{
            var store = this.$store.trip;
            var id = store.active_itinerary_id;
            var itins = store.itineraries || [];
            for (var i = 0; i < itins.length; i++) {{
                if (itins[i].id === id) return itins[i].days || [];
            }}
            return itins.length ? (itins[0].days || []) : [];
        }},
        get attractions() {{ return this.$store.trip.attractions || []; }},
        get dayTrips() {{ return this.$store.trip.day_trips || []; }},

        get scheduledIds() {{
            var ids = new Set();
            (this.days || []).forEach(function(d) {{
                (d.activities || []).forEach(function(a) {{
                    if (a.attraction_id) ids.add(a.attraction_id);
                }});
            }});
            return ids;
        }},

        get unscheduled() {{
            var self = this;
            return (this.attractions || []).filter(function(a) {{
                return !self.scheduledIds.has(a.id) && !a.hidden;
            }});
        }},

        get scheduledDayTripIds() {{
            var ids = new Set();
            (this.days || []).forEach(function(d) {{
                (d.activities || []).forEach(function(a) {{
                    if (a.day_trip_id) ids.add(a.day_trip_id);
                }});
            }});
            return ids;
        }},

        get unscheduledDayTrips() {{
            var self = this;
            return (this.dayTrips || []).filter(function(dt) {{
                return !self.scheduledDayTripIds.has(dt.id) && !dt.hidden;
            }});
        }},

        sortedActivities: function(day) {{
            var acts = (day.activities || []).slice();
            acts.sort(function(a, b) {{
                var ta = a.start_time || 'zz';
                var tb = b.start_time || 'zz';
                return ta.localeCompare(tb);
            }});
            return acts;
        }},

        fmtDuration: function(m) {{
            if (!m) return '';
            if (m < 60) return m + 'min';
            var h = Math.floor(m / 60), r = m % 60;
            return r ? h + 'h' + String(r).padStart(2, '0') : h + 'h';
        }},

        fmtPrice: function(p) {{
            if (p == null) return '';
            return p === 0 ? 'Free' : '\\u20ac' + p;
        }},

        dayName: function(d) {{
            if (!d) return '';
            var dt = new Date(d + 'T00:00:00');
            return ['Sunday','Monday','Tuesday','Wednesday','Thursday','Friday','Saturday'][dt.getDay()];
        }},

        shortDate: function(d) {{
            if (!d) return '';
            var dt = new Date(d + 'T00:00:00');
            var months = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
            return months[dt.getMonth()] + ' ' + dt.getDate();
        }},

        dayStats: function(day) {{
            var hours = 0, cost = 0;
            (day.activities || []).forEach(function(a) {{
                hours += (a.duration_minutes || 0);
                cost += (a.price_eur || 0);
            }});
            return {{
                hours: (hours / 60).toFixed(1),
                cost: Math.round(cost)
            }};
        }},

        /* Inline editing */
        startEdit: function(day, field) {{
            this.editing = {{
                date: day.date,
                field: field,
                value: day[field] || ''
            }};
            var self = this;
            this.$nextTick(function() {{
                var inp = document.querySelector('.day-edit-input:not([style*="display: none"])');
                if (inp) inp.focus();
            }});
        }},

        saveEdit: function() {{
            if (!this.editing) return;
            var self = this;
            var date = this.editing.date;
            var field = this.editing.field;
            var value = this.editing.value;
            this.editing = null;
            var body = {{}};
            body[field] = value || null;
            fetch('/api/days/' + date, {{
                method: 'PATCH',
                headers: {{'Content-Type': 'application/json'}},
                body: JSON.stringify(body)
            }}).then(function() {{
                self.$store.trip.reload();
            }});
        }},

        cancelEdit: function() {{
            this.editing = null;
        }},

        /* SortableJS */
        initAllSortables: function() {{
            var self = this;
            // Destroy old instances
            this._sortables.forEach(function(s) {{ s.destroy(); }});
            this._sortables = [];

            // Pool
            var poolEl = this.$refs.poolList;
            if (poolEl) {{
                this._sortables.push(Sortable.create(poolEl, {{
                    group: 'kanban',
                    sort: false,
                    draggable: '.pool-card',
                    filter: '.card-btn',
                    preventOnFilter: false,
                    ghostClass: 'sortable-ghost',
                    onStart: function() {{ self._dragging = true; }},
                    onEnd: function() {{ setTimeout(function() {{ self._dragging = false; }}, 50); }},
                    onAdd: function(evt) {{
                        // Activity dragged back from a day column
                        var actId = evt.item.dataset.activityId;
                        var fromDate = evt.from.dataset.dayList;
                        // Remove the physically-moved DOM element — Alpine re-render handles it
                        evt.item.parentNode.removeChild(evt.item);
                        if (actId && fromDate) {{
                            self.unscheduleItem(fromDate, actId);
                        }}
                    }}
                }}));
            }}

            // Day columns
            var dayLists = document.querySelectorAll('[data-day-list]');
            dayLists.forEach(function(el) {{
                self._sortables.push(Sortable.create(el, {{
                    group: 'kanban',
                    animation: 150,
                    draggable: '.act-card,[data-attraction-id]',
                    filter: '.card-btn',
                    preventOnFilter: false,
                    ghostClass: 'sortable-ghost',
                    onStart: function() {{ self._dragging = true; }},
                    onAdd: function(evt) {{
                        var targetDate = el.dataset.dayList;
                        var attractionId = evt.item.dataset.attractionId;
                        var activityId = evt.item.dataset.activityId;
                        var fromDate = evt.from.dataset.dayList;
                        // Remove the physically-moved DOM element — Alpine re-render handles it
                        evt.item.parentNode.removeChild(evt.item);

                        if (activityId && fromDate) {{
                            // Move from another day
                            self.moveToDay(activityId, targetDate);
                        }} else if (attractionId) {{
                            // Schedule from pool
                            self.scheduleToDay(attractionId, targetDate);
                        }}
                    }},
                    onEnd: function(evt) {{
                        setTimeout(function() {{ self._dragging = false; }}, 50);
                        // Reorder within same day
                        if (evt.from === evt.to) {{
                            self.reorderDay(el.dataset.dayList, el);
                        }}
                    }}
                }}));
            }});
        }},

        scheduleToDay: function(attractionId, dayDate) {{
            var self = this;
            fetch('/api/schedule', {{
                method: 'POST',
                headers: {{'Content-Type': 'application/json'}},
                body: JSON.stringify({{attraction_id: attractionId, date: dayDate}})
            }}).then(function() {{
                self.$store.trip.reload().then(function() {{
                    self.$nextTick(function() {{ self.initAllSortables(); }});
                }});
            }});
        }},

        unscheduleItem: function(dayDate, activityId) {{
            var self = this;
            fetch('/api/days/' + dayDate + '/activities/' + activityId, {{method: 'DELETE'}}).then(function() {{
                self.$store.trip.reload().then(function() {{
                    self.$nextTick(function() {{ self.initAllSortables(); }});
                }});
            }});
        }},

        moveToDay: function(activityId, targetDate) {{
            var self = this;
            this.$store.trip.moveActivity(activityId, targetDate).then(function() {{
                self.$nextTick(function() {{ self.initAllSortables(); }});
            }});
        }},

        reorderDay: function(dayDate, container) {{
            var ids = Array.from(container.children)
                .map(function(c) {{ return c.dataset.activityId; }})
                .filter(Boolean);
            if (!ids.length) return;
            var self = this;
            fetch('/api/days/' + dayDate + '/activities/reorder', {{
                method: 'PUT',
                headers: {{'Content-Type': 'application/json'}},
                body: JSON.stringify({{activity_ids: ids}})
            }}).then(function() {{
                self.$store.trip.reload();
            }});
        }},

        swapDays: function(date1, date2) {{
            var self = this;
            this.$store.trip.swapDays(date1, date2).then(function() {{
                self.$nextTick(function() {{ self.initAllSortables(); }});
            }});
        }},

        /* Description lookup for activity cards */
        actDescription: function(act) {{
            if (act.attraction_id) {{
                var attr = (this.attractions || []).find(function(a) {{ return a.id === act.attraction_id; }});
                return attr ? attr.description : '';
            }}
            if (act.day_trip_id) {{
                var dt = (this.dayTrips || []).find(function(d) {{ return d.id === act.day_trip_id; }});
                return dt ? dt.description : '';
            }}
            return '';
        }},

    }};
}}
</script>
"""
