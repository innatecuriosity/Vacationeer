# Frontend Guide

Reference for building interactive views in Vacationeer.

---

## 1. Architecture Overview

```
Browser                          Server (FastAPI + uvicorn)
  |                                  |
  |  GET /valencia-app.html          |
  |<---------------------------------|  Static HTML (pre-rendered)
  |                                  |
  |  <script src="alpine CDN">      |
  |  Alpine.store('trip', {...})     |  Trip JSON embedded in page
  |                                  |
  |  PATCH /api/attractions/{id}     |
  |--------------------------------->|  Mutates in-memory Trip
  |  { ...updated attraction }       |  Saves trip.json to disk
  |<---------------------------------|  Rebuilds HTML in background
```

- **FastAPI** serves the app shell (static HTML) and exposes a REST API.
- **Alpine.js** (loaded from CDN, no build step) provides client-side reactivity.
- Trip data is embedded as JSON in the HTML at build time. `Alpine.store('trip', ...)` makes it globally available.
- Every API write persists to `trip.json` on disk and triggers a background HTML rebuild.

---

## 2. API Reference

Base URL: `http://localhost:8080` (default port, configurable with `--port`).

All request/response bodies are JSON. Dates use `YYYY-MM-DD` format. Times use `HH:MM` format.

### Trip

#### `GET /api/trip` --- Full trip

Response `200`:
```json
{
  "id": "a1b2c3d4",
  "name": "Valencia Summer 2026",
  "destination": "Valencia",
  "start_date": "2026-07-10",
  "end_date": "2026-07-20",
  "travelers": 2,
  "budget_eur": 3000,
  "preferences": { "interests": ["food", "architecture"], "avoid": ["crowds"], "pace": "moderate", "budget_per_day_eur": 150 },
  "attractions": [ ... ],
  "day_trips": [ ... ],
  "days": [ ... ]
}
```

#### `PATCH /api/trip` --- Update trip metadata

Request:
```json
{ "name": "Valencia Adventure 2026", "travelers": 3 }
```
Only include fields to change. Allowed fields: `name`, `destination`, `start_date`, `end_date`, `travelers`, `budget_eur`.

Response `200`: full trip object.

---

### Preferences

#### `GET /api/trip/preferences`

Response `200`:
```json
{ "interests": ["food", "architecture"], "avoid": ["crowds"], "pace": "moderate", "budget_per_day_eur": 150 }
```
Returns default `Preferences()` if none set.

#### `PUT /api/trip/preferences` --- Replace preferences

Request:
```json
{ "interests": ["nature", "food"], "avoid": [], "pace": "relaxed", "budget_per_day_eur": 120 }
```

Response `200`: the saved preferences object.

---

### Attractions

#### `GET /api/attractions` --- List all

Response `200`: array of attraction objects.

#### `POST /api/attractions` --- Add new

Request:
```json
{
  "name": "Central Market",
  "description": "Europe's largest fresh food market",
  "location": { "lat": 39.4737, "lng": -0.3790, "address": "Placa de la Ciutat de Bruges" },
  "category": "food",
  "price_eur": 0,
  "duration_minutes": 60,
  "tags": ["market", "free"],
  "tips": "Go early morning for the best selection",
  "url": "https://www.mercadocentralvalencia.es",
  "expected_score": 8.5
}
```
Required fields: `name`, `location` (with `lat` and `lng`), `category`. Everything else is optional.

The server auto-generates an `id` by slugifying the name. Returns `422` if the id already exists.

Response `201`: the created attraction object (with generated `id`).

#### `GET /api/attractions/{id}`

Response `200`:
```json
{
  "id": "central-market",
  "name": "Central Market",
  "location": { "lat": 39.4737, "lng": -0.3790, "address": "Placa de la Ciutat de Bruges" },
  "category": "food",
  "price_eur": 0,
  "duration_minutes": 60,
  ...
}
```
Returns `404` if not found.

#### `PATCH /api/attractions/{id}` --- Partial update

Request (plain dict, not the full Attraction model):
```json
{ "price_eur": 5, "tips": "Updated tip" }
```
The `id` field cannot be changed. Unknown fields are silently ignored.

Response `200`: updated attraction object.

#### `DELETE /api/attractions/{id}`

Response `200`:
```json
{ "ok": true }
```

#### `POST /api/attractions/{id}/score` --- Set user score

Request:
```json
{ "score": 8.5 }
```

Response `200`: updated attraction object with `user_score` set.

---

### Days

Day endpoints use the date string (`YYYY-MM-DD`) as the identifier.

#### `GET /api/days` --- List all days

Response `200`: array of day objects, sorted by date.

#### `POST /api/days` --- Add a day

Request:
```json
{
  "date": "2026-07-11",
  "label": "Old Town Day",
  "notes": "Start early to beat the heat",
  "activities": [
    {
      "name": "City of Arts and Sciences",
      "attraction_id": "city-of-arts-and-sciences",
      "start_time": "09:00",
      "duration_minutes": 180,
      "price_eur": 37,
      "status": "planned"
    }
  ]
}
```
Returns `422` if the date already exists. Days are auto-sorted by date after insertion.

Response `201`: the created day object.

#### `PATCH /api/days/{date}` --- Update day

Request:
```json
{ "label": "Beach & Old Town", "notes": "Revised plan" }
```
The `date` field cannot be changed.

Response `200`: updated day object.

#### `DELETE /api/days/{date}`

Response `200`:
```json
{ "ok": true }
```

---

## 3. Alpine.js Store

Trip data is loaded into a global Alpine store on page load:

```js
Alpine.store('trip', {
  // --- Data (populated from embedded JSON or fetched from API) ---
  ...tripJson,

  // --- Methods ---

  async addAttraction(data) {
    const res = await fetch('/api/attractions', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    });
    const attraction = await res.json();
    this.attractions.push(attraction);
    return attraction;
  },

  async updateAttraction(id, data) {
    const res = await fetch(`/api/attractions/${id}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    });
    const updated = await res.json();
    const idx = this.attractions.findIndex(a => a.id === id);
    if (idx !== -1) this.attractions[idx] = updated;
    return updated;
  },

  async deleteAttraction(id) {
    await fetch(`/api/attractions/${id}`, { method: 'DELETE' });
    this.attractions = this.attractions.filter(a => a.id !== id);
  },

  async setScore(id, score) {
    const res = await fetch(`/api/attractions/${id}/score`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ score })
    });
    const updated = await res.json();
    const idx = this.attractions.findIndex(a => a.id === id);
    if (idx !== -1) this.attractions[idx] = updated;
    return updated;
  },

  async updatePreferences(prefs) {
    const res = await fetch('/api/trip/preferences', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(prefs)
    });
    this.preferences = await res.json();
  },

  async reload() {
    const res = await fetch('/api/trip');
    const data = await res.json();
    Object.assign(this, data);
  }
});
```

### Usage in templates

```html
<!-- Read from store -->
<span x-text="$store.trip.destination"></span>
<span x-text="$store.trip.attractions.length + ' attractions'"></span>

<!-- Call a store method -->
<button @click="$store.trip.deleteAttraction('central-market')">Delete</button>

<!-- Iterate -->
<template x-for="a in $store.trip.attractions" :key="a.id">
  <div x-text="a.name"></div>
</template>
```

---

## 4. Adding New Interactive Views

Views are Python functions that return an HTML string. The string is embedded into the app shell at build time.

### Step-by-step

1. Create a function in `vacationeer/views/your_view.py`:

```python
def render_your_view(trip: Trip) -> str:
    return """
    <div x-data="{ selected: null }">
      <template x-for="a in $store.trip.attractions" :key="a.id">
        <div @click="selected = a.id"
             :class="selected === a.id ? 'selected' : ''">
          <span x-text="a.name"></span>
          <span x-text="a.category"></span>
        </div>
      </template>
    </div>
    """
```

2. Register it in `__main__.py`:

```python
from vacationeer.views.your_view import render_your_view

tab_contents = {
    ...
    "yourview-content": render_your_view(trip),
}
```

3. Add a tab button and panel in `app_shell.py`.

### Key directives

| Directive   | Purpose                          | Example                                    |
|-------------|----------------------------------|--------------------------------------------|
| `x-data`    | Local component state            | `x-data="{ open: false }"`                |
| `x-for`     | Loop over array                  | `x-for="item in $store.trip.attractions"` |
| `x-text`    | Set text content                 | `x-text="item.name"`                      |
| `x-bind`    | Bind attribute (`:` shorthand)   | `:class="active ? 'on' : ''"`             |
| `x-show`    | Toggle visibility                | `x-show="open"`                           |
| `x-on`      | Event handler (`@` shorthand)    | `@click="open = !open"`                   |
| `x-model`   | Two-way bind to input            | `x-model="searchQuery"`                   |
| `x-effect`  | Run side-effect on data change   | `x-effect="console.log(count)"`           |

### Minimal interactive component example

```html
<div x-data="{ query: '', get filtered() {
    return $store.trip.attractions.filter(a =>
      a.name.toLowerCase().includes(this.query.toLowerCase())
    );
  }}">

  <input type="text" x-model="query" placeholder="Search attractions...">

  <template x-for="a in filtered" :key="a.id">
    <div>
      <strong x-text="a.name"></strong>
      <span x-text="a.category"></span>
    </div>
  </template>

  <div x-show="filtered.length === 0">No matches.</div>
</div>
```

---

## 5. Modal System

Modals are controlled via custom DOM events.

### Opening a modal

```js
// Dispatch from Alpine
$dispatch('open-modal', { template: 'edit-attraction', data: { id: 'central-market' } })

// Or from vanilla JS
document.dispatchEvent(new CustomEvent('open-modal', {
  detail: { template: 'edit-attraction', data: { id: 'central-market' } }
}));
```

### Modal container (in app shell)

```html
<div x-data="{ show: false, template: '', modalData: {} }"
     @open-modal.window="show = true; template = $event.detail.template; modalData = $event.detail.data"
     @close-modal.window="show = false"
     @keydown.escape.window="show = false"
     x-show="show"
     style="position:fixed;inset:0;z-index:1000;display:flex;align-items:center;justify-content:center;">

  <!-- Backdrop -->
  <div @click="show = false"
       style="position:absolute;inset:0;background:rgba(0,0,0,0.5);"></div>

  <!-- Content -->
  <div style="position:relative;background:#fff;border-radius:12px;padding:24px;
              max-width:500px;width:90%;max-height:80vh;overflow-y:auto;">
    <template x-if="template === 'edit-attraction'">
      <!-- Edit attraction form here -->
    </template>
    <button @click="$dispatch('close-modal')"
            style="position:absolute;top:12px;right:12px;background:none;border:none;
                   font-size:18px;cursor:pointer;">x</button>
  </div>
</div>
```

### Closing

- Press Escape
- Click backdrop
- Dispatch `close-modal` event
- Call `$dispatch('close-modal')` from inside modal content

---

## 6. Toast Notifications

Dispatch a `toast` custom event to show a brief notification.

### Dispatching

```js
// From Alpine
$dispatch('toast', { message: 'Attraction saved', type: 'success' })

// Types: 'success' | 'error' | 'info'
```

### Toast container

```html
<div x-data="{ toasts: [] }"
     @toast.window="
       let t = { ...$event.detail, id: Date.now() };
       toasts.push(t);
       setTimeout(() => toasts = toasts.filter(x => x.id !== t.id), 3000)
     "
     style="position:fixed;bottom:20px;right:20px;z-index:2000;display:flex;flex-direction:column;gap:8px;">
  <template x-for="t in toasts" :key="t.id">
    <div :style="`padding:12px 20px;border-radius:8px;color:#fff;font-size:14px;
                   background:${t.type === 'error' ? '#E74C3C' : t.type === 'success' ? '#27AE60' : '#2980B9'};
                   box-shadow:0 2px 8px rgba(0,0,0,0.15);`"
         x-text="t.message">
    </div>
  </template>
</div>
```

Auto-dismisses after 3 seconds. No manual close needed (user can ignore).

---

## 7. Styling Conventions

### Color palette

| Role            | Hex       | Usage                        |
|-----------------|-----------|------------------------------|
| Primary dark    | `#1a2332` | Sidebar, headings, buttons   |
| Accent blue     | `#4ea4f6` | Active tab indicator         |
| Background      | `#ffffff` | Main content area            |
| Section bg      | `#f5f6f8` | Tab content backgrounds      |
| Border          | `#e8eaed` | Header border, dividers      |
| Text primary    | `#1a2332` | Headings, body text          |
| Text secondary  | `#5f6b7a` | Meta info, labels            |
| Text muted      | `#8893a2` | Placeholders, hints          |
| Score green     | `#27AE60` | Score >= 8, free price       |
| Score yellow    | `#F1C40F` | Score 6-8                    |
| Score red       | `#E74C3C` | Score < 6, errors            |
| Price orange    | `#E67E22` | Paid items                   |
| Tip background  | `#FFF9E6` | Tip callout boxes            |
| Tip border      | `#F1C40F` | Tip left border              |

### Category colors

| Category        | Hex       |
|-----------------|-----------|
| `landmark`      | `#C0392B` |
| `museum`        | `#2980B9` |
| `nature`        | `#27AE60` |
| `food`          | `#E67E22` |
| `entertainment` | `#8E44AD` |
| `transport`     | `#7F8C8D` |
| `accommodation` | `#922B21` |
| `shopping`      | `#2E86C1` |
| `day_trip`      | `#1E8449` |

### CSS conventions

- **All styles are inline** in the HTML strings. No external CSS files.
- Class names are descriptive, kebab-case (e.g., `ov-card`, `tl-day-tab`, `nav-btn`).
- Use classes only when JS needs to query elements; otherwise prefer inline styles.
- Font stack: `system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif`
- Border radius: `8px`-`12px` for cards, `20px` for pills/badges.
- Box shadow for cards: `0 1px 4px rgba(0,0,0,0.06)` (subtle) or `0 1px 4px rgba(0,0,0,0.07)`.

---

## 8. Development Workflow

```bash
# Install dependencies
pip install pydantic folium click fastapi uvicorn

# Run dev server (serves app + API, auto-rebuilds HTML on data changes)
python -m vacationeer serve trips/valencia-2026/trip.json

# Optional: specify port
python -m vacationeer serve trips/valencia-2026/trip.json --port 3000

# Static build only (no server, generates HTML files in output/)
python -m vacationeer build trips/valencia-2026/trip.json

# Quick info about a trip file
python -m vacationeer info trips/valencia-2026/trip.json
```

The dev server:
- Loads `trip.json` into memory on startup.
- Serves pre-built HTML from `output/` as static files.
- Exposes the REST API at `/api/*`.
- On every API write, saves `trip.json` and rebuilds HTML in a background task.
- Opens the browser automatically on start.

---

## 9. PWA Roadmap

Planned steps to make Vacationeer installable on mobile:

1. **`manifest.json`** -- app name, icons (192px + 512px), `theme_color: #1a2332`, `display: standalone`.
2. **Service worker** -- cache-first strategy for app shell and API responses.
3. **Offline map tiles** -- pre-cache CartoDB Voyager tiles for the target city bounding box.
4. **IndexedDB** -- store trip data locally; sync back to server when online.
5. **Deploy** -- any static host or VPS (Railway, Fly.io, VPS with nginx). Once served over HTTPS, the app becomes installable on Android via "Add to Home Screen".

No changes to the current architecture are needed. The FastAPI server already works as a PWA backend.

---

## 10. For Agents

### API contract (quick ref)

```
GET    /api/trip                      Full trip JSON
PATCH  /api/trip                      Update metadata (name, destination, dates, travelers, budget_eur)
GET    /api/trip/preferences          Get preferences
PUT    /api/trip/preferences          Replace preferences
GET    /api/attractions               List attractions
POST   /api/attractions               Add attraction (required: name, location, category)
GET    /api/attractions/{id}          Get one attraction
PATCH  /api/attractions/{id}          Partial update (dict, not model)
DELETE /api/attractions/{id}          Delete attraction
POST   /api/attractions/{id}/score    Set user_score (body: {score: float})
GET    /api/days                      List days (sorted by date)
POST   /api/days                      Add day (required: date)
PATCH  /api/days/{date}               Update day (label, notes, activities)
DELETE /api/days/{date}               Delete day
```

All writes save to `trip.json` and trigger background HTML rebuild.

### Store methods

```
$store.trip.addAttraction(data)        POST /api/attractions
$store.trip.updateAttraction(id, data) PATCH /api/attractions/{id}
$store.trip.deleteAttraction(id)       DELETE /api/attractions/{id}
$store.trip.setScore(id, score)        POST /api/attractions/{id}/score
$store.trip.updatePreferences(prefs)   PUT /api/trip/preferences
$store.trip.reload()                   GET /api/trip (full refresh)
```

### Adding interactivity to a view

1. Write a Python function returning an HTML string.
2. Use `x-data` for local state, `$store.trip` for global data.
3. Use `@click`, `x-for`, `x-text`, `x-show`, `x-bind` for reactivity.
4. Call store methods for API writes; dispatch `toast` for feedback.
5. Register the view in `__main__.py` tab_contents and add a nav tab in `app_shell.py`.

### File ownership map

```
vacationeer/models/trip.py        Pydantic models (Trip, Attraction, Day, etc.)
vacationeer/server.py             FastAPI app factory, all API endpoints
vacationeer/storage/json_store.py Load/save trip.json
vacationeer/views/app_shell.py    Main HTML shell, sidebar, tab switching
vacationeer/views/overview.py     Overview tab (attraction cards by category)
vacationeer/views/timeline.py     Timeline tab (day tabs, activity list)
vacationeer/views/chat.py         Chat tab (UI mockup)
vacationeer/maps/generator.py     Folium map generation
vacationeer/__main__.py           CLI commands (map, info, build, serve)
trips/*/trip.json                  Trip data files
```
