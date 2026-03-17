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
<div style="background:#f5f6f8;padding:20px;border-radius:12px;
            font-family:system-ui,-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;"
     x-data="{{
       filter: 'all',
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
           price_eur: a.price_eur,
           duration_minutes: a.duration_minutes,
           tips: a.tips || '',
           url: a.url || '',
           tags: (a.tags || []).join(', '),
           expected_score: a.expected_score
         }};
       }},
       saveEdit(id) {{
         let f = this.editForm;
         let tags = f.tags ? f.tags.split(',').map(t => t.trim()).filter(Boolean) : [];
         $store.trip.updateAttraction(id, {{
           name: f.name,
           description: f.description || null,
           price_eur: f.price_eur != null && f.price_eur !== '' ? parseFloat(f.price_eur) : null,
           duration_minutes: f.duration_minutes != null && f.duration_minutes !== '' ? parseInt(f.duration_minutes) : null,
           tips: f.tips || null,
           url: f.url || null,
           tags: tags,
           expected_score: f.expected_score != null && f.expected_score !== '' ? parseFloat(f.expected_score) : null
         }});
         this.editing = null;
       }}
     }}">

  <!-- ===== Trip summary header ===== -->
  <div style="background:#1a2332;color:#fff;padding:24px 28px;border-radius:12px;margin-bottom:20px;">
    <h2 style="margin:0 0 8px 0;font-size:24px;" x-text="$store.trip.destination"></h2>
    <div style="display:flex;gap:24px;flex-wrap:wrap;font-size:14px;opacity:0.9;">
      <span>&#x1f4c5; <span x-text="$store.trip.start_date + ' &ndash; ' + $store.trip.end_date"></span></span>
      <span>&#x1f465; <span x-text="$store.trip.travelers"></span> traveler<span x-show="$store.trip.travelers !== 1">s</span></span>
      <span>&#x1f4b0; Budget: <span x-text="$store.trip.budget_eur ? fmtPrice($store.trip.budget_eur) : 'Not set'"></span></span>
      <span x-text="($store.trip.attractions || []).length + ' attractions'" style="font-weight:600;"></span>
    </div>
  </div>

  <!-- ===== Category filter bar ===== -->
  <div style="margin-bottom:16px;padding:16px;background:#fff;border-radius:10px;
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

  <!-- ===== Search & Sort bar ===== -->
  <div style="display:flex;gap:12px;margin-bottom:20px;flex-wrap:wrap;align-items:center;">
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
    <div style="background:#fff;border-radius:12px;box-shadow:0 2px 12px rgba(0,0,0,0.12);margin-bottom:20px;border:1px solid #e8ecf1;"
         :style="'border-left:5px solid ' + catColor(attraction.category)">

      <!-- ===== Collapsed card header ===== -->
      <div x-show="editing !== attraction.id"
           @click="expanded = expanded === attraction.id ? null : attraction.id"
           style="padding:12px 16px;cursor:pointer;user-select:none;">
        <div style="display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:4px;">
          <div style="display:flex;align-items:center;gap:6px;min-width:0;flex:1;">
            <h4 style="margin:0;font-size:14px;color:#1a2332;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;"
                x-text="attraction.name"></h4>

            <!-- Category pill -->
            <span :style="'display:inline-block;padding:2px 8px;border-radius:10px;font-size:11px;font-weight:600;color:#fff;background:' + catColor(attraction.category)"
                  x-text="catLabel(attraction.category)"></span>

            <!-- Expected score bar (compact) -->
            <span x-show="attraction.expected_score != null"
                  style="display:inline-flex;align-items:center;gap:4px;margin-left:8px;">
              <span style="display:inline-block;width:60px;height:8px;background:#e0e0e0;border-radius:4px;overflow:hidden;vertical-align:middle;">
                <span :style="'display:block;height:100%;border-radius:4px;background:' + scoreColor(attraction.expected_score) + ';width:' + scorePct(attraction.expected_score) + '%'"></span>
              </span>
              <span :style="'font-size:12px;font-weight:600;color:' + scoreColor(attraction.expected_score)"
                    x-text="(attraction.expected_score || 0).toFixed(1)"></span>
            </span>

            <!-- User score compact -->
            <span x-show="attraction.user_score != null"
                  :style="'margin-left:6px;font-size:11px;font-weight:600;color:' + scoreColor(attraction.user_score)">
              You: &#x2605; <span x-text="(attraction.user_score || 0).toFixed(1)"></span>
            </span>
          </div>
          <div style="display:flex;align-items:center;gap:6px;flex-shrink:0;">
            <!-- Price pill -->
            <span :style="'display:inline-block;padding:2px 10px;border-radius:12px;font-size:12px;font-weight:600;border:1px solid;'
                          + ((attraction.price_eur == null || attraction.price_eur === 0)
                             ? 'background:#27AE6022;color:#27AE60;border-color:#27AE6044;'
                             : 'background:#E67E2222;color:#E67E22;border-color:#E67E2244;')"
                  x-text="fmtPrice(attraction.price_eur)"></span>
            <!-- Duration -->
            <span x-show="attraction.duration_minutes" style="font-size:12px;color:#666;">
              &#x23f1; <span x-text="fmtDuration(attraction.duration_minutes)"></span>
            </span>
            <!-- Chevron -->
            <span style="font-size:12px;color:#999;transition:transform 0.2s;display:inline-block;"
                  :style="expanded === attraction.id ? 'transform:rotate(180deg)' : ''">&#x25BC;</span>
          </div>
        </div>
        <!-- Short description -->
        <div x-show="expanded !== attraction.id && attraction.description"
             style="font-size:13px;color:#666;margin-top:6px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:100%;"
             x-text="attraction.description"></div>
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
          <div style="display:flex;gap:10px;flex-wrap:wrap;">
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
            <label style="font-size:12px;color:#666;display:block;margin-bottom:2px;">Tags (comma separated)</label>
            <input x-model="editForm.tags" placeholder="tag1, tag2, tag3"
                   style="width:100%;padding:8px 12px;border:2px solid #ddd;border-radius:6px;font-size:14px;outline:none;box-sizing:border-box;"
                   @focus="$el.style.borderColor='#1a2332'" @blur="$el.style.borderColor='#ddd'">
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
