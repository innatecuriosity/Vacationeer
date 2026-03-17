# Vacationeer — Project Overview

A local-first travel planning app. Python-based PoC generating static HTML, designed to eventually run on Android.

## Vision
Pipeline from questionnaire (preferences, people, budget, must-dos) → workspace/itinerary with list, timelines, and map. Editable via AI chat or manually. Exportable to phone for offline use.

## Name
Vacationeer (like a musketeer).

## Tech Stack (current)
- **Language**: Python 3.12+
- **Models**: Pydantic v2
- **Map**: Folium (Leaflet.js) with CartoDB Voyager tiles
- **CLI**: Click
- **Output**: Static HTML (single-file app with embedded CSS/JS)
- **Server**: Python `http.server` for local preview

## Tech Stack (future considerations)
- Android: Flet, Kivy, or PWA approach
- Backend: FastAPI for real-time features (chat, sync)
- AI: Claude API for chat-based editing and auto-planning

---

## Project Structure

```
VacationeerPoc/
├── vacationeer/
│   ├── __main__.py          # CLI: map, info, build, serve
│   ├── models/
│   │   ├── __init__.py      # Exports: Trip, Attraction, Activity, Day, Category, Preferences
│   │   └── trip.py          # Pydantic models
│   ├── maps/
│   │   └── generator.py     # Folium map generation
│   └── views/
│       ├── __init__.py
│       ├── app_shell.py     # Main HTML shell with sidebar
│       ├── overview.py      # Attractions overview tab
│       ├── timeline.py      # Daily timeline tab
│       └── chat.py          # Chat interface tab
├── trips/
│   └── valencia-2026/
│       └── trip.json        # Sample trip data (32 attractions)
├── data/
│   └── valencia-2026/       # Source markdown files
├── docs/
│   ├── PROJECT.md           # This file
│   └── timeline-architecture.md
└── output/                  # Generated HTML files
```

---

## Core Entities

### Attraction
A place or thing to visit. Has location, category, price, duration, tags, tips, URL, and scores.
- `expected_score` (0-10): AI-predicted match based on user preferences
- `user_score` (0-10): User's personal rating, empty by default

### Activity
A scheduled instance of an attraction (or custom event) in a day. Has start_time, duration, price, status (planned/confirmed/done/skipped), notes. Links to attraction via `attraction_id`.

### Day
A date with a label and ordered list of activities. Days can be swapped around easily.

### Trip
Top-level container: destination, dates, travelers, budget, preferences, attractions (backlog), days (schedule).

### Preferences
User's interests, things to avoid, pace (relaxed/moderate/packed), daily budget.

### Categories
landmark, museum, nature, food, entertainment, transport, accommodation, shopping, day_trip

---

## CLI Commands

```bash
python -m vacationeer map <trip.json>      # Generate map HTML only
python -m vacationeer info <trip.json>     # Show trip summary
python -m vacationeer build <trip.json>    # Generate full app (map + all tabs)
python -m vacationeer serve <trip.json>    # Build + local server + open browser
```

---

## Feature Status

### Implemented
- [x] **Data models** — Trip, Attraction, Activity, Day, Preferences with Pydantic
- [x] **Map** — Interactive Folium map with:
  - CartoDB Voyager tiles (works offline/local)
  - Circle markers color-coded by category
  - Styled hover popups (card layout, price badges, tips, links)
  - Toggleable text labels showing attraction names
  - Category legend
  - Layer control for filtering by category
- [x] **App shell** — Single HTML page with:
  - Dark navy (#1a2332) sidebar with Map/Overview/Timeline/Chat tabs
  - Responsive (collapses to icons on mobile)
  - Trip header with metadata
- [x] **Overview tab** — Attractions grouped by category:
  - Colored left border per category
  - Expandable cards (click to reveal full details)
  - Score bars (green 8+, yellow 6-8, red <6)
  - Tags as pills, tips box, URL buttons
  - Image placeholder for future scraping
- [x] **Timeline tab** — Basic structure:
  - Day tab bar, activity list with status dots
  - Placeholder when no days planned
- [x] **Chat tab** — UI mockup only:
  - Message bubbles (AI left, user right)
  - Disabled input bar
- [x] **Sample data** — Valencia 2026 trip with 32 attractions + 3 day trips
- [x] **CLI** — map, info, build, serve commands

### Planned — Timeline (see docs/timeline-architecture.md)
- [ ] Proportional time-axis (1 min = 1.5px, variable-height blocks)
- [ ] Backlog sidebar (unscheduled attractions)
- [ ] Transit segments between activities (walking time via haversine)
- [ ] Free time gap visualization
- [ ] Day stats in headers (cost, walking distance, activity count)
- [ ] CLI: `schedule`, `unschedule`, `swap-days`, `move-activity`, `init-days`
- [ ] CLI: `auto-plan` (geographic clustering + nearest-neighbor TSP)
- [ ] Map sync via postMessage (highlight day's attractions + route polyline)

### Planned — Interactive Features
- [ ] Embed trip data as JSON in HTML for client-side editing
- [ ] Drag-and-drop reordering of activities
- [ ] Drag attractions from backlog into days
- [ ] Click-to-edit time/duration/notes
- [ ] "Save" button (download JSON or POST to local server)

### Planned — Chat / AI
- [ ] Connect chat to Claude API for natural language editing
- [ ] AI-suggested day plans based on preferences + proximity
- [ ] "Add attraction" via chat
- [ ] "Reorganize day" via chat

### Planned — Scoring & Filtering
- [ ] Map filtering by score range
- [ ] Map filtering by user_score vs expected_score
- [ ] Auto-compute expected_score from preferences (keyword matching)
- [ ] User score input UI (star rating or slider)

### Planned — Data & Content
- [ ] Attraction image scraping (from URLs or search)
- [ ] Weather data integration for date-based planning
- [ ] Opening hours / seasonal availability
- [ ] Price currency conversion

### Planned — Mobile / Offline
- [ ] PWA wrapper or Flet/Kivy build for Android
- [ ] Offline map tile caching
- [ ] Export trip as self-contained package for phone
- [ ] Cloud sync for multi-device editing

---

## Design Decisions

### Why static HTML generation?
Simple, works offline, no server needed. Good enough for PoC. Migration trigger: when real-time bidirectional state is needed (working chat, collaborative editing).

### Why not a JS framework?
Keeping it Python-only for now. The HTML generation approach lets us iterate fast. When we outgrow it, FastAPI backend + lightweight frontend (Svelte/HTMX) is the path.

### Color theme
- Primary: dark navy `#1a2332`
- Background: white `#ffffff`, sections `#f5f6f8`
- Category colors: red (landmark), blue (museum), green (nature), orange (food), purple (entertainment), gray (transport), darkred (accommodation), cadetblue (shopping), darkgreen (day_trip)

### Category colors (hex)
```
landmark:      #C0392B
museum:        #2980B9
nature:        #27AE60
food:          #E67E22
entertainment: #8E44AD
transport:     #7F8C8D
accommodation: #922B21
shopping:      #2E86C1
day_trip:      #1E8449
```

---

## Working with This Project

### Quick start
```bash
cd VacationeerPoc
pip install pydantic folium click
python -m vacationeer serve trips/valencia-2026/trip.json
```

### Adding attractions
Edit `trips/valencia-2026/trip.json` — add entries to the `attractions` array following the existing format. All fields except `id`, `name`, `location`, and `category` are optional.

### Rebuilding
```bash
python -m vacationeer build trips/valencia-2026/trip.json
# Output: output/valencia-map.html + output/valencia-app.html
```

### For agents working on this project
- Read this file first for context
- Read `docs/timeline-architecture.md` for timeline-specific plans
- Models are in `vacationeer/models/trip.py` — always check current schema
- Views generate HTML strings — all CSS/JS is inline (no external deps)
- Map uses Folium — tiles must work without Referer header (no OSM tiles)
- Color theme: navy #1a2332 + white, category colors listed above
- Test with: `python -m vacationeer build trips/valencia-2026/trip.json`
