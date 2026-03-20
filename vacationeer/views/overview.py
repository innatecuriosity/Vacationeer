from __future__ import annotations

from vacationeer.models.trip import Trip, Category
from vacationeer.theme import CATEGORY_META, SCORE_GREEN, SCORE_YELLOW, SCORE_RED


def _build_category_color_js() -> str:
    pairs = ", ".join(
        f"'{cat.value}': '{info.color}'" for cat, info in CATEGORY_META.items()
    )
    return "{" + pairs + "}"


def _build_category_label_js() -> str:
    pairs = ", ".join(
        f"'{cat.value}': '{info.label}'" for cat, info in CATEGORY_META.items()
    )
    return "{" + pairs + "}"


def _build_category_icon_js() -> str:
    pairs = ", ".join(
        f"'{cat.value}': '{info.html_icon}'" for cat, info in CATEGORY_META.items()
    )
    return "{" + pairs + "}"


def render_overview(trip: Trip) -> str:
    """Return HTML string for the overview tab content.

    The returned markup is an Alpine.js reactive template.  Actual data is
    read from ``$store.trip`` at runtime; the *trip* parameter is only used
    to bake category-colour mappings into the CSS.
    """
    cat_colors_js = _build_category_color_js()
    cat_labels_js = _build_category_label_js()
    cat_icons_js = _build_category_icon_js()

    return f"""
<style>
@media (max-width: 768px) {{
    .ov-wrap {{ padding: 10px !important; }}
    .ov-summary {{ padding: 16px !important; }}
    .ov-summary h2 {{ font-size: 20px !important; }}
    .ov-summary .ov-meta {{ font-size: 12px !important; gap: 10px !important; }}
    .ov-filter-bar {{ padding: 10px !important; }}
    .ov-filter-bar button {{ padding: 6px 12px !important; font-size: 12px !important; min-height: 36px !important; }}
    .ov-search-bar {{ gap: 8px !important; }}
    .ov-search-bar input {{ min-width: 0 !important; width: 100% !important; }}
    .ov-card-header {{ padding: 12px !important; }}
    .ov-card-body {{ padding: 12px !important; }}
    .ov-edit-row {{ flex-direction: column !important; }}
    .ov-edit-row > div {{ min-width: 0 !important; }}
}}
@media (max-width: 480px) {{
    .ov-wrap {{ padding: 6px !important; }}
    .ov-summary {{ padding: 12px 14px !important; margin-bottom: 12px !important; }}
    .ov-summary h2 {{ font-size: 18px !important; }}
    .ov-filter-bar {{ padding: 8px !important; margin-bottom: 10px !important; }}
    .ov-filter-bar button {{ padding: 5px 10px !important; font-size: 11px !important; }}
}}
</style>
<div class="ov-wrap" style="background:#f5f6f8;padding:20px;border-radius:12px;
            font-family:system-ui,-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;"
     x-data="{{
       filter: 'all',
       groupFilter: 'all',
       search: '',
       sortBy: 'category',
       showHidden: false,
       catColors: {cat_colors_js},
       catLabels: {cat_labels_js},
       catIcons: {cat_icons_js},
       catColor(c) {{ return this.catColors[c] || '#888'; }},
       catLabel(c) {{ return this.catLabels[c] || c; }},
       catIcon(c) {{ return this.catIcons[c] || ''; }},
       scoreColor(s) {{ return s >= 8 ? '{SCORE_GREEN}' : s >= 6 ? '{SCORE_YELLOW}' : '{SCORE_RED}'; }},
       scorePct(s) {{ return Math.min((s / 10) * 100, 100); }},
       fmtPrice(p) {{
         if (p == null || p === 0) return 'Free';
         return p === Math.floor(p) ? '\u20ac' + p : '\u20ac' + p.toFixed(2);
       }},
       fmtDuration(m) {{
         if (m == null) return '';
         if (m < 60) return m + 'min';
         var h = Math.floor(m / 60), r = m % 60;
         return r ? h + 'h ' + r + 'min' : h + 'h';
       }},
       filtered() {{
         let list = $store.trip.attractions || [];
         if (!this.showHidden) list = list.filter(a => !a.hidden);
         if (this.filter !== 'all') list = list.filter(a => a.category === this.filter);
         if (this.groupFilter !== 'all') {{
           let grp = ($store.trip.groupings || []).find(g => g.id === this.groupFilter);
           if (grp) list = list.filter(a => (grp.member_ids || []).includes(a.id));
         }}
         if (this.search.trim()) {{
           let q = this.search.trim().toLowerCase();
           list = list.filter(a => a.name.toLowerCase().includes(q));
         }}
         let key = this.sortBy;
         return [...list].sort((a, b) => {{
           if (key === 'name') return (a.name || '').localeCompare(b.name || '');
           if (key === 'expected_score') return (b.expected_score || 0) - (a.expected_score || 0);
           if (key === 'user_score') return (b.user_score || 0) - (a.user_score || 0);
           if (key === 'price') return (a.price_eur || 0) - (b.price_eur || 0);
           if (key === 'category') return (a.category || '').localeCompare(b.category || '');
           return 0;
         }});
       }}
     }}">

  <!-- ===== Trip summary header ===== -->
  <div class="ov-summary" style="background:#1a2332;color:#fff;padding:24px 28px;border-radius:12px;margin-bottom:20px;">
    <h2 style="margin:0 0 8px 0;font-size:24px;" x-text="$store.trip.destination"></h2>
    <div class="ov-meta" style="display:flex;gap:24px;flex-wrap:wrap;font-size:14px;opacity:0.9;">
      <span>&#x1f4c5; <span x-text="$store.trip.start_date + ' &ndash; ' + $store.trip.end_date"></span></span>
      <span>&#x1f465; <span x-text="$store.trip.travelers"></span> traveler<span x-show="$store.trip.travelers !== 1">s</span></span>
      <span>&#x1f4b0; Budget: <span x-text="$store.trip.budget_eur ? fmtPrice($store.trip.budget_eur) : 'Not set'"></span></span>
      <span x-text="($store.trip.attractions || []).length + ' attractions'" style="font-weight:600;"></span>
    </div>
  </div>

  <!-- ===== Category filter bar ===== -->
  <div class="ov-filter-bar" style="margin-bottom:16px;padding:16px;background:#fff;border-radius:10px;
              box-shadow:0 1px 4px rgba(0,0,0,0.06);">
    <div style="font-size:13px;color:#888;margin-bottom:8px;text-transform:uppercase;letter-spacing:0.5px;">
      Filter by Category
    </div>
    <div style="display:flex;flex-wrap:wrap;gap:6px;">
      <button @click="filter = 'all'"
              :style="'display:inline-block;padding:4px 14px;border-radius:20px;font-size:13px;font-weight:500;cursor:pointer;border:2px solid #1a2332;transition:all .15s;'
                      + (filter === 'all' ? 'background:#1a2332;color:#fff;' : 'background:#fff;color:#1a2332;')"
      >All (<span x-text="($store.trip.attractions || []).length"></span>)</button>

      <template x-for="cat in [...new Set(($store.trip.attractions || []).map(a => a.category))]" :key="cat">
        <button @click="filter = cat"
                :style="'display:inline-block;padding:4px 14px;border-radius:20px;font-size:13px;font-weight:500;cursor:pointer;border:2px solid ' + catColor(cat) + ';transition:all .15s;'
                        + (filter === cat ? 'background:' + catColor(cat) + ';color:#fff;' : 'background:#fff;color:' + catColor(cat) + ';')">
          <span x-text="catLabel(cat)"></span>
          (<span x-text="($store.trip.attractions || []).filter(a => a.category === cat).length"></span>)
        </button>
      </template>
    </div>
  </div>

  <!-- ===== Grouping filter bar ===== -->
  <div class="ov-filter-bar" x-show="($store.trip.groupings || []).length"
       style="margin-bottom:16px;padding:16px;background:#fff;border-radius:10px;
              box-shadow:0 1px 4px rgba(0,0,0,0.06);">
    <div style="font-size:13px;color:#888;margin-bottom:8px;text-transform:uppercase;letter-spacing:0.5px;">
      Filter by Grouping
    </div>
    <div style="display:flex;flex-wrap:wrap;gap:6px;">
      <button @click="groupFilter = 'all'"
              :style="'display:inline-block;padding:4px 14px;border-radius:20px;font-size:13px;font-weight:500;cursor:pointer;border:2px solid #1a2332;transition:all .15s;'
                      + (groupFilter === 'all' ? 'background:#1a2332;color:#fff;' : 'background:#fff;color:#1a2332;')"
      >All</button>

      <template x-for="grp in ($store.trip.groupings || [])" :key="grp.id">
        <button @click="groupFilter = grp.id"
                :style="'display:inline-block;padding:4px 14px;border-radius:20px;font-size:13px;font-weight:500;cursor:pointer;border:2px solid ' + (grp.color || '#888') + ';transition:all .15s;'
                        + (groupFilter === grp.id ? 'background:' + (grp.color || '#888') + ';color:#fff;' : 'background:#fff;color:' + (grp.color || '#888') + ';')">
          <span x-text="grp.name"></span>
          (<span x-text="(grp.member_ids || []).length"></span>)
        </button>
      </template>
    </div>
  </div>

  <!-- ===== Search & Sort bar ===== -->
  <div class="ov-search-bar" style="display:flex;gap:12px;margin-bottom:20px;flex-wrap:wrap;align-items:center;">
    <input type="text" x-model="search" placeholder="Search attractions..."
           style="flex:1;min-width:200px;padding:10px 14px;border:2px solid #ddd;border-radius:8px;font-size:14px;
                  outline:none;transition:border-color .15s;"
           @focus="$el.style.borderColor='#1a2332'" @blur="$el.style.borderColor='#ddd'">
    <select x-model="sortBy"
            style="padding:10px 14px;border:2px solid #ddd;border-radius:8px;font-size:14px;
                   background:#fff;cursor:pointer;outline:none;"
            @focus="$el.style.borderColor='#1a2332'" @blur="$el.style.borderColor='#ddd'">
      <option value="name">Sort: Name</option>
      <option value="expected_score">Sort: Expected Score</option>
      <option value="user_score">Sort: Your Score</option>
      <option value="price">Sort: Price</option>
      <option value="category">Sort: Category</option>
    </select>
    <label style="display:flex;align-items:center;gap:6px;font-size:13px;color:#888;cursor:pointer;white-space:nowrap;padding:4px 0;">
      <input type="checkbox" x-model="showHidden" style="accent-color:#888;">
      &#x1f47b; Show hidden
    </label>
  </div>

  <!-- ===== Empty state ===== -->
  <div x-show="!($store.trip.attractions || []).length"
       style="text-align:center;padding:40px 20px;color:#999;">
    <div style="font-size:32px;margin-bottom:12px;">&#x1f5fa;</div>
    <p style="font-size:15px;">No attractions added yet. Use the chat to discover places!</p>
  </div>

  <!-- ===== No results state ===== -->
  <div x-show="($store.trip.attractions || []).length && !filtered().length"
       style="text-align:center;padding:40px 20px;color:#999;">
    <div style="font-size:28px;margin-bottom:12px;">&#x1f50d;</div>
    <p style="font-size:15px;">No attractions match your filters.</p>
  </div>

  <!-- ===== Attraction cards ===== -->
  <template x-for="attraction in filtered()" :key="attraction.id">
    <div :style="'background:#fff;border-radius:8px;box-shadow:0 2px 10px rgba(0,0,0,0.10);margin-bottom:8px;border:1px solid #d1d5db;border-left:6px solid ' + catColor(attraction.category)"
         @click="window.dispatchEvent(new CustomEvent('open-attraction', {{detail: {{id: attraction.id}}}}))"
         style="cursor:pointer;">

      <div class="ov-card-header" style="padding:12px 16px;user-select:none;">
        <!-- Row 1: Name + Google Maps pin + description snippet -->
        <div style="display:flex;align-items:baseline;gap:8px;min-width:0;">
          <span x-show="attraction.visited" style="color:#27ae60;font-size:14px;flex-shrink:0" title="Visited">&#x2705;</span>
          <span x-show="attraction.hidden" style="font-size:14px;flex-shrink:0;opacity:.5" title="Hidden">&#x1f47b;</span>
          <h4 style="margin:0;font-size:15px;color:#1a2332;white-space:nowrap;flex-shrink:0;"
              :style="attraction.hidden ? 'opacity:.5' : ''"
              x-text="attraction.name"></h4>
          <a :href="googleMapsUrl(attraction.location, attraction.name)" target="_blank" rel="noopener"
             @click.stop title="Open in Google Maps"
             style="flex-shrink:0;color:#4285f4;font-size:14px;opacity:0.7;text-decoration:none;line-height:1;">&#x1f4cd;</a>
          <span x-show="attraction.description"
                style="font-size:13px;color:#888;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;min-width:0;flex:1;"
                x-text="attraction.description"></span>
        </div>
        <!-- Row 2: Category, score, duration, price — compact badges -->
        <div style="display:flex;align-items:center;gap:8px;margin-top:6px;flex-wrap:wrap;">
          <!-- Category pill -->
          <span :style="'display:inline-block;padding:2px 8px;border-radius:10px;font-size:11px;font-weight:600;color:#fff;background:' + catColor(attraction.category)"
                x-text="catLabel(attraction.category)"></span>
          <!-- Grouping pills + quick add -->
          <template x-for="grp in ($store.trip.groupings || []).filter(g => (g.member_ids || []).includes(attraction.id))" :key="grp.id">
            <span :style="'display:inline-block;padding:1px 7px;border-radius:10px;font-size:10px;font-weight:500;color:#fff;background:' + (grp.color || '#888') + ';margin-left:4px;'"
                  x-text="grp.name"></span>
          </template>
          <span x-show="($store.trip.groupings || []).length" x-data="{{ gpOpen: false }}" style="position:relative;display:inline-block;">
            <button @click.stop="gpOpen = !gpOpen" type="button"
              style="display:inline-flex;align-items:center;justify-content:center;width:20px;height:20px;border-radius:50%;border:1px dashed #aaa;background:#fff;color:#888;font-size:12px;cursor:pointer;line-height:1;padding:0;"
              title="Add to grouping">+</button>
            <div x-show="gpOpen" @click.outside="gpOpen = false" x-transition
                 style="position:absolute;top:24px;left:0;z-index:50;background:#fff;border:1px solid #e2e5e9;border-radius:8px;padding:6px;box-shadow:0 4px 12px rgba(0,0,0,.15);display:flex;flex-wrap:wrap;gap:4px;min-width:140px;">
              <template x-for="grp in ($store.trip.groupings || [])" :key="grp.id">
                <button type="button" @click.stop="$store.trip.toggleGroupingMember(grp.id, attraction.id)"
                  :style="'display:inline-flex;align-items:center;padding:3px 10px;border-radius:12px;font-size:11px;font-weight:500;cursor:pointer;border:1px solid ' + (grp.color || '#888') + ';transition:all .15s;white-space:nowrap;'
                    + ((grp.member_ids || []).includes(attraction.id) ? 'background:' + (grp.color || '#888') + ';color:#fff;' : 'background:#fff;color:' + (grp.color || '#888') + ';')"
                  x-text="grp.name"></button>
              </template>
            </div>
          </span>
          <!-- Expected score -->
          <span x-show="attraction.expected_score != null"
                style="display:inline-flex;align-items:center;gap:3px;">
            <span style="display:inline-block;width:40px;height:6px;background:#e0e0e0;border-radius:3px;overflow:hidden;">
              <span :style="'display:block;height:100%;border-radius:3px;background:' + scoreColor(attraction.expected_score) + ';width:' + scorePct(attraction.expected_score) + '%'"></span>
            </span>
            <span :style="'font-size:11px;font-weight:600;color:' + scoreColor(attraction.expected_score)"
                  x-text="(attraction.expected_score || 0).toFixed(1)"></span>
          </span>
          <!-- User score -->
          <span x-show="attraction.user_score != null"
                :style="'font-size:11px;font-weight:600;color:' + scoreColor(attraction.user_score)">
            &#x2605; <span x-text="(attraction.user_score || 0).toFixed(1)"></span>
          </span>
          <!-- Duration -->
          <span x-show="attraction.duration_minutes" style="font-size:11px;color:#666;">
            &#x23f1; <span x-text="fmtDuration(attraction.duration_minutes)"></span>
          </span>
          <!-- Price -->
          <span :style="'font-size:11px;font-weight:600;'
                        + ((attraction.price_eur == null || attraction.price_eur === 0)
                           ? 'color:#27AE60;' : 'color:#E67E22;')"
                x-text="fmtPrice(attraction.price_eur)"></span>
        </div>
      </div>

    </div>
  </template>
</div>
"""
