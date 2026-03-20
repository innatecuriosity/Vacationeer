from __future__ import annotations

import json

from vacationeer.models.trip import Trip, Category
from vacationeer.theme import CATEGORY_META, GROUPING_PALETTE, SCORE_GREEN, SCORE_YELLOW, SCORE_RED


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
    cat_options = "\n".join(
        f'                <option value="{c.value}">{info.label}</option>'
        for c, info in CATEGORY_META.items()
    )

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
       expanded: null,
       editing: null,
       editForm: {{}},
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
       }},
       startEdit(a) {{
         this.editing = a.id;
         this.editForm = {{
           name: a.name,
           description: a.description || '',
           category: a.category || 'landmark',
           price_eur: a.price_eur,
           duration_minutes: a.duration_minutes,
           tips: a.tips || '',
           url: a.url || '',
           tags: [].concat(a.tags || []),
           tagInput: '',
           expected_score: a.expected_score
         }};
       }},
       addTag() {{
         let v = this.editForm.tagInput.replace(/,/g, '').trim();
         if (v && !this.editForm.tags.includes(v)) this.editForm.tags.push(v);
         this.editForm.tagInput = '';
       }},
       removeTag(i) {{ this.editForm.tags.splice(i, 1); }},
       allTags() {{
         let s = new Set();
         ($store.trip.attractions || []).forEach(function(a) {{ (a.tags || []).forEach(function(t) {{ s.add(t); }}); }});
         return Array.from(s).sort();
       }},
       saveEdit(id) {{
         let f = this.editForm;
         $store.trip.updateAttraction(id, {{
           name: f.name,
           description: f.description || null,
           category: f.category,
           price_eur: f.price_eur != null && f.price_eur !== '' ? parseFloat(f.price_eur) : null,
           duration_minutes: f.duration_minutes != null && f.duration_minutes !== '' ? parseInt(f.duration_minutes) : null,
           tips: f.tips || null,
           url: f.url || null,
           tags: f.tags,
           expected_score: f.expected_score != null && f.expected_score !== '' ? parseFloat(f.expected_score) : null
         }});
         this.editing = null;
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
    <div :style="'background:#fff;border-radius:8px;box-shadow:0 2px 10px rgba(0,0,0,0.10);margin-bottom:8px;border:1px solid #d1d5db;border-left:6px solid ' + catColor(attraction.category)">

      <!-- ===== Collapsed card header ===== -->
      <div x-show="editing !== attraction.id"
           @click="expanded = expanded === attraction.id ? null : attraction.id"
           style="padding:12px 16px;cursor:pointer;user-select:none;">
        <!-- Row 1: Name — short description -->
        <div style="display:flex;align-items:baseline;gap:8px;min-width:0;">
          <h4 style="margin:0;font-size:15px;color:#1a2332;white-space:nowrap;flex-shrink:0;"
              x-text="attraction.name"></h4>
          <span x-show="attraction.description && expanded !== attraction.id"
                style="font-size:13px;color:#888;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;min-width:0;flex:1;"
                x-text="attraction.description"></span>
          <!-- Chevron -->
          <span style="font-size:11px;color:#999;transition:transform 0.2s;display:inline-block;flex-shrink:0;margin-left:auto;"
                :style="expanded === attraction.id ? 'transform:rotate(180deg)' : ''">&#x25BC;</span>
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

      <!-- ===== Expanded content ===== -->
      <div x-show="expanded === attraction.id && editing !== attraction.id"
           x-transition:enter="transition ease-out duration-200"
           x-transition:enter-start="opacity-0"
           x-transition:enter-end="opacity-100"
           style="padding:0 16px 14px 16px;border-top:1px solid #f0f0f0;">

        <!-- Full description -->
        <p x-show="attraction.description"
           style="margin:10px 0;font-size:13px;color:#555;line-height:1.6;"
           x-text="attraction.description"></p>

        <!-- Scores detail -->
        <div x-show="attraction.expected_score != null || attraction.user_score != null"
             style="margin:10px 0;padding:10px 12px;background:#f8f9fa;border-radius:8px;">
          <!-- Expected score detail -->
          <div x-show="attraction.expected_score != null"
               style="display:flex;align-items:center;gap:8px;margin-bottom:4px;">
            <span style="font-size:13px;color:#666;min-width:70px;">Expected</span>
            <span style="display:inline-block;width:100px;height:10px;background:#e0e0e0;border-radius:5px;overflow:hidden;">
              <span :style="'display:block;height:100%;border-radius:5px;background:' + scoreColor(attraction.expected_score) + ';width:' + scorePct(attraction.expected_score) + '%'"></span>
            </span>
            <span :style="'font-size:13px;font-weight:600;color:' + scoreColor(attraction.expected_score)"
                  x-text="(attraction.expected_score || 0).toFixed(1) + '/10'"></span>
          </div>
          <!-- User score detail -->
          <div x-show="attraction.user_score != null"
               style="display:flex;align-items:center;gap:8px;margin-bottom:4px;">
            <span style="font-size:13px;color:#666;min-width:70px;">Your score</span>
            <span style="display:inline-block;width:100px;height:10px;background:#e0e0e0;border-radius:5px;overflow:hidden;">
              <span :style="'display:block;height:100%;border-radius:5px;background:' + scoreColor(attraction.user_score) + ';width:' + scorePct(attraction.user_score) + '%'"></span>
            </span>
            <span :style="'font-size:13px;font-weight:600;color:' + scoreColor(attraction.user_score)"
                  x-text="(attraction.user_score || 0).toFixed(1) + '/10'"></span>
          </div>
        </div>

        <!-- Star rating (clickable, 1-10) -->
        <div style="margin:10px 0;" @click.stop>
          <div style="font-size:11px;color:#999;margin-bottom:4px;text-transform:uppercase;letter-spacing:0.5px;">Rate this attraction</div>
          <div style="display:flex;align-items:center;gap:2px;">
            <template x-for="s in [1,2,3,4,5,6,7,8,9,10]" :key="s">
              <span @click="$store.trip.setScore(attraction.id, s)"
                    :style="'cursor:pointer;font-size:20px;transition:color .1s;color:' + (s <= (attraction.user_score || 0) ? '#f39c12' : '#ddd')"
                    style="cursor:pointer;">&#x2605;</span>
            </template>
            <span x-show="attraction.user_score"
                  style="margin-left:8px;font-size:13px;font-weight:600;color:#f39c12;"
                  x-text="(attraction.user_score || 0) + '/10'"></span>
          </div>
        </div>

        <!-- Tags -->
        <div x-show="attraction.tags && attraction.tags.length"
             style="margin:8px 0;">
          <div style="font-size:11px;color:#999;margin-bottom:4px;text-transform:uppercase;letter-spacing:0.5px;">Tags</div>
          <div style="display:flex;flex-wrap:wrap;gap:4px;">
            <template x-for="tag in (attraction.tags || [])" :key="tag">
              <span style="display:inline-block;padding:3px 10px;border-radius:12px;background:#e8ecf1;color:#4a5568;font-size:11px;font-weight:500;"
                    x-text="tag"></span>
            </template>
          </div>
        </div>

        <!-- Groupings -->
        <div x-show="($store.trip.groupings || []).length"
             style="margin:8px 0;" @click.stop>
          <div style="font-size:11px;color:#999;margin-bottom:4px;text-transform:uppercase;letter-spacing:0.5px;">Groupings</div>
          <div style="display:flex;flex-wrap:wrap;gap:6px;">
            <template x-for="grp in ($store.trip.groupings || [])" :key="grp.id">
              <label :style="'display:inline-flex;align-items:center;gap:4px;padding:3px 10px;border-radius:12px;font-size:11px;font-weight:500;cursor:pointer;border:1px solid ' + (grp.color || '#888') + ';'
                             + ((grp.member_ids || []).includes(attraction.id) ? 'background:' + (grp.color || '#888') + ';color:#fff;' : 'background:#fff;color:' + (grp.color || '#888') + ';')">
                <input type="checkbox"
                       :checked="(grp.member_ids || []).includes(attraction.id)"
                       @change="$store.trip.toggleGroupingMember(grp.id, attraction.id)"
                       :style="'accent-color:' + (grp.color || '#888') + ';cursor:pointer;width:12px;height:12px;margin:0;'">
                <span x-text="grp.name"></span>
              </label>
            </template>
          </div>
        </div>

        <!-- Tips -->
        <div x-show="attraction.tips"
             style="margin:10px 0;padding:10px 14px;background:#FFF9E6;border-left:3px solid #F1C40F;border-radius:0 8px 8px 0;
                    font-size:13px;color:#7D6608;line-height:1.5;">
          <strong>&#x1f4a1; Tip:</strong> <span x-text="attraction.tips"></span>
        </div>

        <!-- URL link -->
        <div x-show="attraction.url" style="margin:8px 0;">
          <a :href="attraction.url" target="_blank" rel="noopener"
             style="display:inline-block;padding:6px 14px;background:#1a2332;color:#fff;border-radius:6px;font-size:12px;font-weight:500;text-decoration:none;">
            &#x1f517; Visit website</a>
        </div>

        <!-- Image (only if available) -->
        <div x-show="attraction.image_url" style="margin:10px 0;">
          <img :src="attraction.image_url" :alt="attraction.name"
               style="width:100%;max-height:200px;object-fit:cover;border-radius:8px;" />
        </div>

        <!-- Action buttons -->
        <div style="display:flex;gap:8px;margin-top:10px;">
          <button @click.stop="startEdit(attraction)"
                  style="padding:8px 16px;background:#1a2332;color:#fff;border:none;border-radius:6px;font-size:13px;font-weight:500;cursor:pointer;">
            &#x270f; Edit</button>
          <button @click.stop="if(confirm('Delete ' + attraction.name + '?')) $store.trip.deleteAttraction(attraction.id)"
                  style="padding:8px 16px;background:#E74C3C;color:#fff;border:none;border-radius:6px;font-size:13px;font-weight:500;cursor:pointer;">
            &#x1f5d1; Delete</button>
        </div>
      </div>

      <!-- ===== Inline edit form ===== -->
      <div x-show="editing === attraction.id"
           @click.stop
           style="padding:16px;border-top:1px solid #f0f0f0;">
        <h4 style="margin:0 0 12px 0;font-size:15px;color:#1a2332;">Edit Attraction</h4>
        <div style="display:flex;flex-direction:column;gap:10px;">
          <div>
            <label style="font-size:12px;color:#666;display:block;margin-bottom:2px;">Name</label>
            <input x-model="editForm.name" placeholder="Name"
                   style="width:100%;padding:8px 12px;border:2px solid #ddd;border-radius:6px;font-size:14px;outline:none;box-sizing:border-box;"
                   @focus="$el.style.borderColor='#1a2332'" @blur="$el.style.borderColor='#ddd'">
          </div>
          <div>
            <label style="font-size:12px;color:#666;display:block;margin-bottom:2px;">Description</label>
            <textarea x-model="editForm.description" placeholder="Description" rows="3"
                      style="width:100%;padding:8px 12px;border:2px solid #ddd;border-radius:6px;font-size:14px;outline:none;resize:vertical;box-sizing:border-box;"
                      @focus="$el.style.borderColor='#1a2332'" @blur="$el.style.borderColor='#ddd'"></textarea>
          </div>
          <div>
            <label style="font-size:12px;color:#666;display:block;margin-bottom:2px;">Category</label>
            <select x-model="editForm.category"
                    style="width:100%;padding:8px 12px;border:2px solid #ddd;border-radius:6px;font-size:14px;outline:none;box-sizing:border-box;background:#fff;"
                    @focus="$el.style.borderColor='#1a2332'" @blur="$el.style.borderColor='#ddd'">
{cat_options}
            </select>
          </div>
          <div class="ov-edit-row" style="display:flex;gap:10px;flex-wrap:wrap;">
            <div style="flex:1;min-width:120px;">
              <label style="font-size:12px;color:#666;display:block;margin-bottom:2px;">Price (&euro;)</label>
              <input type="number" x-model="editForm.price_eur" placeholder="0" min="0" step="0.01"
                     style="width:100%;padding:8px 12px;border:2px solid #ddd;border-radius:6px;font-size:14px;outline:none;box-sizing:border-box;"
                     @focus="$el.style.borderColor='#1a2332'" @blur="$el.style.borderColor='#ddd'">
            </div>
            <div style="flex:1;min-width:120px;">
              <label style="font-size:12px;color:#666;display:block;margin-bottom:2px;">Duration (min)</label>
              <input type="number" x-model="editForm.duration_minutes" placeholder="60" min="0" step="5"
                     style="width:100%;padding:8px 12px;border:2px solid #ddd;border-radius:6px;font-size:14px;outline:none;box-sizing:border-box;"
                     @focus="$el.style.borderColor='#1a2332'" @blur="$el.style.borderColor='#ddd'">
            </div>
            <div style="flex:1;min-width:120px;">
              <label style="font-size:12px;color:#666;display:block;margin-bottom:2px;">Expected Score</label>
              <input type="number" x-model="editForm.expected_score" placeholder="7.5" min="0" max="10" step="0.1"
                     style="width:100%;padding:8px 12px;border:2px solid #ddd;border-radius:6px;font-size:14px;outline:none;box-sizing:border-box;"
                     @focus="$el.style.borderColor='#1a2332'" @blur="$el.style.borderColor='#ddd'">
            </div>
          </div>
          <div>
            <label style="font-size:12px;color:#666;display:block;margin-bottom:2px;">Tags</label>
            <div style="display:flex;flex-wrap:wrap;gap:4px;padding:6px 10px;border:2px solid #ddd;border-radius:6px;min-height:38px;align-items:center;box-sizing:border-box;background:#fff;"
                 @click="$refs.tagIn.focus()">
              <template x-for="(tag, ti) in editForm.tags" :key="ti">
                <span style="display:inline-flex;align-items:center;gap:3px;padding:2px 8px;border-radius:10px;background:#e8ecf1;color:#4a5568;font-size:12px;font-weight:500;">
                  <span x-text="tag"></span>
                  <button type="button" @click="removeTag(ti)" style="background:none;border:none;color:#999;cursor:pointer;font-size:14px;line-height:1;padding:0 2px;">&times;</button>
                </span>
              </template>
              <input x-model="editForm.tagInput" x-ref="tagIn"
                     @keydown.enter.prevent="addTag()"
                     @keydown.comma.prevent="addTag()"
                     @keydown.backspace="if (!editForm.tagInput && editForm.tags.length) editForm.tags.pop()"
                     list="tag-suggestions"
                     placeholder="Add tag..."
                     style="border:none;outline:none;font-size:13px;min-width:80px;flex:1;padding:2px 0;background:transparent;">
              <datalist id="tag-suggestions">
                <template x-for="t in allTags().filter(t => !editForm.tags.includes(t))" :key="t">
                  <option :value="t"></option>
                </template>
              </datalist>
            </div>
          </div>
          <!-- Grouping picker (direct mode — toggles immediately) -->
          <div x-data="{{
            showNew: false,
            newName: '',
            newColor: '{GROUPING_PALETTE[0]}',
            gpPalette: {json.dumps(GROUPING_PALETTE)},
            async createAndAdd() {{
              if (!this.newName.trim()) return;
              var res = await $store.trip.addGrouping({{ name: this.newName.trim(), color: this.newColor }});
              if (res.ok && res.grouping) {{
                await $store.trip.toggleGroupingMember(res.grouping.id, attraction.id);
              }}
              this.newName = ''; this.showNew = false;
            }}
          }}">
            <label style="font-size:12px;color:#666;display:block;margin-bottom:4px;">Groupings</label>
            <div style="display:flex;flex-wrap:wrap;gap:5px;align-items:center;">
              <template x-for="grp in ($store.trip.groupings || [])" :key="grp.id">
                <button type="button"
                  @click="$store.trip.toggleGroupingMember(grp.id, attraction.id)"
                  :style="'display:inline-flex;align-items:center;gap:4px;padding:4px 12px;border-radius:14px;font-size:12px;font-weight:500;cursor:pointer;border:2px solid ' + (grp.color || '#888') + ';transition:all .15s;'
                    + ((grp.member_ids || []).includes(attraction.id) ? 'background:' + (grp.color || '#888') + ';color:#fff;' : 'background:#fff;color:' + (grp.color || '#888') + ';')"
                  x-text="grp.name"></button>
              </template>
              <button type="button" @click="showNew = !showNew"
                style="display:inline-flex;align-items:center;justify-content:center;width:28px;height:28px;border-radius:50%;border:2px dashed #aaa;background:#fff;color:#888;font-size:16px;cursor:pointer;line-height:1;"
                title="New grouping">+</button>
            </div>
            <!-- Inline new grouping form -->
            <div x-show="showNew" x-transition
                 style="margin-top:6px;padding:8px 10px;border:1px solid #e2e5e9;border-radius:8px;background:#fafafa;display:flex;flex-wrap:wrap;gap:6px;align-items:center;">
              <input x-model="newName" placeholder="Grouping name" @keydown.enter="createAndAdd()"
                     style="flex:1;min-width:100px;padding:4px 8px;border:1px solid #ddd;border-radius:6px;font-size:13px;outline:none;">
              <div style="display:flex;gap:3px;">
                <template x-for="c in gpPalette.slice(0, 8)" :key="c">
                  <button type="button" @click="newColor = c"
                    :style="'width:20px;height:20px;border-radius:50%;border:2px solid ' + (newColor === c ? '#333' : 'transparent') + ';background:' + c + ';cursor:pointer;'"></button>
                </template>
              </div>
              <button type="button" @click="createAndAdd()"
                style="padding:4px 10px;background:#27AE60;color:#fff;border:none;border-radius:6px;font-size:12px;font-weight:600;cursor:pointer;">Add</button>
            </div>
          </div>
          <div>
            <label style="font-size:12px;color:#666;display:block;margin-bottom:2px;">Tips</label>
            <input x-model="editForm.tips" placeholder="Helpful tips..."
                   style="width:100%;padding:8px 12px;border:2px solid #ddd;border-radius:6px;font-size:14px;outline:none;box-sizing:border-box;"
                   @focus="$el.style.borderColor='#1a2332'" @blur="$el.style.borderColor='#ddd'">
          </div>
          <div>
            <label style="font-size:12px;color:#666;display:block;margin-bottom:2px;">URL</label>
            <input x-model="editForm.url" placeholder="https://..."
                   style="width:100%;padding:8px 12px;border:2px solid #ddd;border-radius:6px;font-size:14px;outline:none;box-sizing:border-box;"
                   @focus="$el.style.borderColor='#1a2332'" @blur="$el.style.borderColor='#ddd'">
          </div>
          <div style="display:flex;gap:8px;margin-top:4px;">
            <button @click="saveEdit(attraction.id)"
                    style="padding:8px 20px;background:#27AE60;color:#fff;border:none;border-radius:6px;font-size:13px;font-weight:600;cursor:pointer;">
              Save</button>
            <button @click="editing = null"
                    style="padding:8px 20px;background:#fff;color:#666;border:2px solid #ddd;border-radius:6px;font-size:13px;font-weight:500;cursor:pointer;">
              Cancel</button>
          </div>
        </div>
      </div>

    </div>
  </template>
</div>
"""
