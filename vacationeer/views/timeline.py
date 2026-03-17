from __future__ import annotations

from vacationeer.models.trip import Trip
from vacationeer.theme import BG_LIGHT, BG_WHITE, BORDER, CATEGORY_META, PRIMARY, STATUS_COLORS


def render_timeline(trip: Trip) -> str:
    """Return HTML string for the timeline tab content."""

    # Build category color map for JS
    cat_colors_js = ", ".join(
        f"'{cat.value}': '{info.color}'"
        for cat, info in CATEGORY_META.items()
    )

    return f"""
    <div x-data="{{{{
        activeDay: 0,
        daySortable: null,
        poolSortable: null,
        catColors: {{{{{cat_colors_js}}}}},
        catColor(c) {{{{ return this.catColors[c] || '#999'; }}}},

        get days() {{{{ return this.$store.trip.days || []; }}}},
        get attractions() {{{{ return this.$store.trip.attractions || []; }}}},
        get currentDay() {{{{ return this.days[this.activeDay]; }}}},
        get scheduledIds() {{{{
            var ids = new Set();
            (this.days || []).forEach(function(d) {{{{
                (d.activities || []).forEach(function(a) {{{{
                    if (a.attraction_id) ids.add(a.attraction_id);
                }}}});
            }}}});
            return ids;
        }}}},
        get unscheduled() {{{{
            var self = this;
            return (this.attractions || []).filter(function(a) {{{{
                return !self.scheduledIds.has(a.id);
            }}}});
        }}}},

        initSortable() {{{{
            var self = this;
            if (this.daySortable) {{{{ this.daySortable.destroy(); this.daySortable = null; }}}}
            if (this.poolSortable) {{{{ this.poolSortable.destroy(); this.poolSortable = null; }}}}

            var dayEl = this.$refs.dayActivities;
            if (dayEl) {{{{
                this.daySortable = Sortable.create(dayEl, {{{{
                    group: 'timeline',
                    animation: 150,
                    handle: '.drag-handle',
                    onEnd: function() {{{{ self.reorderItems(); }}}},
                    onAdd: function(evt) {{{{
                        var attractionId = evt.item.dataset.attractionId;
                        if (attractionId) self.scheduleItem(attractionId);
                    }}}}
                }}}});
            }}}}

            var poolEl = this.$refs.poolList;
            if (poolEl) {{{{
                this.poolSortable = Sortable.create(poolEl, {{{{
                    group: 'timeline',
                    sort: false,
                    onAdd: function(evt) {{{{
                        var activityId = evt.item.dataset.activityId;
                        if (activityId) self.unscheduleItem(activityId);
                    }}}}
                }}}});
            }}}}
        }}}},

        async scheduleItem(attractionId) {{{{
            if (!this.currentDay) return;
            var dayDate = this.currentDay.date;
            await fetch('/api/schedule', {{{{
                method: 'POST',
                headers: {{{{'Content-Type': 'application/json'}}}},
                body: JSON.stringify({{{{attraction_id: attractionId, date: dayDate}}}})
            }}}});
            await this.$store.trip.reload();
        }}}},

        async unscheduleItem(activityId) {{{{
            if (!this.currentDay) return;
            var dayDate = this.currentDay.date;
            await fetch('/api/days/' + dayDate + '/activities/' + activityId, {{{{method: 'DELETE'}}}});
            await this.$store.trip.reload();
        }}}},

        async reorderItems() {{{{
            if (!this.currentDay) return;
            var dayDate = this.currentDay.date;
            var el = this.$refs.dayActivities;
            if (!el) return;
            var ids = Array.from(el.children).map(function(c) {{{{ return c.dataset.activityId; }}}}).filter(Boolean);
            await this.$store.trip.reorderActivities(dayDate, ids);
            await this.$store.trip.reload();
        }}}}
    }}}}" x-init="$nextTick(function() {{{{ initSortable(); }}}})"
         style="background:{BG_LIGHT};padding:20px;border-radius:12px;font-family:system-ui,-apple-system,sans-serif;">

        <!-- Day tabs bar -->
        <div style="display:flex;flex-wrap:wrap;gap:4px;margin-bottom:16px;">
            <template x-for="(day, i) in days" :key="i">
                <button @click="activeDay = i; $nextTick(function() {{{{ initSortable(); }}}})"
                        :style="activeDay === i ? 'background:{PRIMARY};color:#fff;' : 'background:#e8ecf1;color:{PRIMARY};'"
                        style="padding:8px 16px;border-radius:20px;border:none;cursor:pointer;font-weight:600;font-size:13px;">
                    <span x-text="day.label || ('Day ' + (i+1))"></span>
                </button>
            </template>
        </div>

        <!-- Split panel -->
        <div class="tl-split" style="display:flex;gap:16px;min-height:400px;">
            <!-- LEFT: Day timeline -->
            <div style="flex:3;background:{BG_WHITE};border-radius:10px;padding:16px;box-shadow:0 1px 4px rgba(0,0,0,0.07);">
                <h4 style="margin:0 0 12px 0;font-size:15px;color:{PRIMARY};">
                    <span x-text="currentDay ? (currentDay.label || currentDay.date) : 'Select a day'"></span>
                </h4>
                <div x-ref="dayActivities" style="min-height:200px;">
                    <template x-for="activity in (currentDay ? currentDay.activities : [])" :key="activity.id">
                        <div :data-activity-id="activity.id" :data-attraction-id="activity.attraction_id"
                             style="display:flex;align-items:center;gap:10px;padding:10px 12px;margin-bottom:8px;background:#f8f9fa;border-radius:8px;border-left:3px solid;cursor:grab;"
                             :style="'border-left-color:' + catColor(activity.category)">
                            <span class="drag-handle" style="cursor:grab;color:#bbb;font-size:16px;">&#x2630;</span>
                            <div style="flex:1;min-width:0;">
                                <div style="font-weight:600;font-size:14px;color:{PRIMARY};" x-text="activity.name"></div>
                                <div style="font-size:12px;color:#888;">
                                    <span x-show="activity.start_time" x-text="activity.start_time"></span>
                                    <span x-show="activity.duration_minutes"> &middot; <span x-text="activity.duration_minutes + 'min'"></span></span>
                                </div>
                            </div>
                        </div>
                    </template>
                    <div x-show="!currentDay || !(currentDay.activities || []).length"
                         style="text-align:center;padding:40px 20px;color:#999;font-size:14px;">
                        Drag attractions here to schedule them
                    </div>
                </div>
            </div>

            <!-- RIGHT: Unscheduled pool -->
            <div style="flex:2;background:{BG_WHITE};border-radius:10px;padding:16px;box-shadow:0 1px 4px rgba(0,0,0,0.07);">
                <h4 style="margin:0 0 12px 0;font-size:15px;color:{PRIMARY};">
                    Unscheduled (<span x-text="unscheduled.length"></span>)
                </h4>
                <div x-ref="poolList" style="min-height:200px;">
                    <template x-for="attr in unscheduled" :key="attr.id">
                        <div :data-attraction-id="attr.id"
                             style="display:flex;align-items:center;gap:10px;padding:10px 12px;margin-bottom:8px;background:#f8f9fa;border-radius:8px;border-left:3px solid;cursor:grab;"
                             :style="'border-left-color:' + catColor(attr.category)">
                            <span class="drag-handle" style="cursor:grab;color:#bbb;font-size:16px;">&#x2630;</span>
                            <div style="flex:1;min-width:0;">
                                <div style="font-weight:600;font-size:14px;color:{PRIMARY};" x-text="attr.name"></div>
                                <div style="font-size:12px;color:#888;">
                                    <span x-show="attr.duration_minutes" x-text="attr.duration_minutes + 'min'"></span>
                                    <span x-show="attr.price_eur != null"
                                          x-text="attr.price_eur === 0 ? 'Free' : '\\u20ac' + attr.price_eur"></span>
                                </div>
                            </div>
                        </div>
                    </template>
                    <div x-show="!unscheduled.length"
                         style="text-align:center;padding:40px 20px;color:#999;font-size:14px;">
                        All attractions are scheduled!
                    </div>
                </div>
            </div>
        </div>

        <style>
            @media (max-width: 768px) {{{{
                .tl-split {{{{ flex-direction: column; }}}}
            }}}}
        </style>
    </div>
    """
