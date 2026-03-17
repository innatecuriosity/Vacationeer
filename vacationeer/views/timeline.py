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
    font-size: 12px;
    padding: 2px 6px;
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
}}
.act-card:hover {{
    box-shadow: 0 2px 6px rgba(0,0,0,0.1);
}}
.act-card .drag-handle {{
    cursor: grab;
    color: #bbb;
    font-size: 14px;
    flex-shrink: 0;
    line-height: 1;
    margin-top: 2px;
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
.act-card .act-remove {{
    margin-left: auto;
    background: none;
    border: none;
    cursor: pointer;
    color: #ccc;
    font-size: 16px;
    flex-shrink: 0;
    padding: 0 2px;
}}
.act-card .act-remove:hover {{
    color: #e74c3c;
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
/* Mobile */
@media (max-width: 768px) {{
    .kanban {{
        flex-direction: column;
        height: auto;
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
    }}
    .day-col {{
        width: 100%;
        min-width: 100%;
        max-height: 400px;
    }}
}}
</style>

<div class="kanban" x-data="kanbanTimeline()" x-init="$nextTick(function() {{ initAllSortables(); }})">

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
            <div class="card-name" x-text="attr.name"></div>
            <div class="card-meta">
              <span x-show="attr.duration_minutes" x-text="fmtDuration(attr.duration_minutes)"></span>
              <span x-show="attr.price_eur != null" x-text="fmtPrice(attr.price_eur)"></span>
              <span x-show="attr.expected_score" :style="'color:' + (attr.expected_score >= 8 ? '#27AE60' : attr.expected_score >= 6 ? '#F1C40F' : '#E74C3C')"
                    x-text="'\\u2605' + (attr.expected_score||0).toFixed(1)"></span>
            </div>
          </div>
        </div>
      </template>
      <!-- Day trips -->
      <template x-for="dt in unscheduledDayTrips" :key="dt.id">
        <div class="pool-card" :data-daytrip-id="dt.id"
             style="border-left-color:#1E8449;">
          <div style="flex:1;min-width:0;">
            <div class="card-name" x-text="dt.name"></div>
            <div class="card-meta" style="color:#1E8449;">Day Trip</div>
          </div>
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
                <span class="day-num">Day <span x-text="i+1"></span></span>
                <span class="day-date" x-text="formatDate(day.date)"></span>
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
                <span class="drag-handle">&#x2630;</span>
                <div style="flex:1;min-width:0;">
                  <div style="display:flex;align-items:center;gap:6px;">
                    <span class="card-time" x-show="act.start_time" x-text="act.start_time || ''"></span>
                    <span class="card-name" x-text="act.name"></span>
                  </div>
                  <div class="card-meta">
                    <span x-show="act.duration_minutes" x-text="fmtDuration(act.duration_minutes)"></span>
                    <span x-show="act.notes" x-text="act.notes" style="color:#888;font-style:italic;"></span>
                  </div>
                </div>
                <button class="act-remove" @click="unscheduleItem(day.date, act.id)"
                        title="Remove">&times;</button>
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

<script>
function kanbanTimeline() {{
    return {{
        _sortables: [],
        editing: null,
        catColors: {{{cat_colors_js}}},

        catColor: function(c) {{ return this.catColors[c] || '#999'; }},

        get days() {{ return this.$store.trip.days || []; }},
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
                return !self.scheduledIds.has(a.id);
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
                return !self.scheduledDayTripIds.has(dt.id);
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

        formatDate: function(d) {{
            if (!d) return '';
            var parts = d.split('-');
            var months = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
            return months[parseInt(parts[1])-1] + ' ' + parseInt(parts[2]);
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
                    ghostClass: 'sortable-ghost',
                    onAdd: function(evt) {{
                        // Activity dragged back from a day column
                        var actId = evt.item.dataset.activityId;
                        var fromDate = evt.from.dataset.dayList;
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
                    handle: '.drag-handle',
                    draggable: '.act-card,[data-attraction-id]',
                    ghostClass: 'sortable-ghost',
                    onAdd: function(evt) {{
                        var targetDate = el.dataset.dayList;
                        var attractionId = evt.item.dataset.attractionId;
                        var activityId = evt.item.dataset.activityId;
                        var fromDate = evt.from.dataset.dayList;

                        if (activityId && fromDate) {{
                            // Move from another day
                            self.moveToDay(activityId, targetDate);
                        }} else if (attractionId) {{
                            // Schedule from pool
                            self.scheduleToDay(attractionId, targetDate);
                        }}
                    }},
                    onEnd: function(evt) {{
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
        }}
    }};
}}
</script>
"""
