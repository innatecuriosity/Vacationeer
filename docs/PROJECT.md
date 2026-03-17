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
- **Server**: FastAPI + uvicorn for local preview (with API endpoints)

## Tech Stack (future considerations)
- Android: Flet, Kivy, or PWA approach
- Backend: FastAPI for real-time features (chat, sync)
- AI: Claude API for chat-based editing and auto-planning

---

## Project Structure

```
VacationeerPoc/
├── vacationeer/
│   ├── __main__.py          # CLI: map, info, build, serve + scheduling commands
│   ├── models/
│   │   ├── __init__.py      # Exports all models
│   │   └── trip.py          # Pydantic models (see Core Entities below)
│   ├── storage/
│   │   ├── base.py          # TripStore Protocol (abstract interface)
│   │   └── json_store.py    # JsonTripStore implementation
│   ├── planning/
│   │   └── scheduler.py     # Pure scheduling functions (init_days, schedule, etc.)
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
│       └── trip.json        # Sample trip data (29 attractions + 3 day trips)
├── data/
│   └── valencia-2026/       # Source markdown files
├── docs/
│   ├── PROJECT.md           # This file
│   └── timeline-architecture.md
└── output/                  # Generated HTML files
```

---

## Core Entities

All models are defined in `vacationeer/models/trip.py` using Pydantic v2.

### Attraction
A place or thing to visit. Has location, category, price, duration, tags, tips, URL, and scores.
- `expected_score` (0-10): AI-predicted match based on user preferences
- `user_score` (0-10): User's personal rating, empty by default

### Activity
A scheduled instance of an attraction (or custom event) in a day. Links to source via:
- `attraction_id` — references an Attraction
- `day_trip_id` — references a DayTrip (for activities expanded from a day trip)
- `category` — denormalized from attraction for display without lookup
- `travel_from_prev_minutes` — transit time from the previous activity
- `start_time`, `duration_minutes`, `price_eur`, `status` (planned/confirmed/done/skipped), `notes`

### Day
A date with a label, optional `start_time`, and ordered list of activities. Days can be swapped around easily.

### DayTrip
A composite entity grouping a destination with its sub-attractions and travel logistics. Lives on `trip.day_trips` (separate from regular attractions). Fields:
- `destination`, `location`, `description` — the destination itself
- `sub_attractions: list[Attraction]` — things to visit at the destination
- `outbound: TravelSegment` — how to get there (train, bus, etc.)
- `return_trip: TravelSegment` — how to get back
- `total_price_eur`, `total_duration_minutes`, `tags`, `tips`, scores

When scheduled onto a Day via `schedule-day-trip`, a DayTrip expands into individual Activities (outbound travel + each sub-attraction + return travel), all linked back via `day_trip_id`.

### TravelSegment
Transport between locations: `mode` (train/bus/car/walk/boat/metro), `origin`, `destination`, optional departure/arrival times, `duration_minutes`, `price_eur`, `booking_reference`, `notes`.

### Trip
Top-level container: destination, dates, travelers, budget, preferences, `attractions` (backlog of regular places), `day_trips` (composite day trip entities), `days` (the schedule).

### Preferences
User's interests, things to avoid, pace (relaxed/moderate/packed), daily budget.

### Categories
landmark, museum, nature, food, entertainment, transport, accommodation, shopping, day_trip

### TravelMode
train, bus, car, walk, boat, metro

---

## CLI Commands

### Build & Serve
```bash
python -m vacationeer map <trip.json>      # Generate map HTML only
python -m vacationeer info <trip.json>     # Show trip summary
python -m vacationeer build <trip.json>    # Generate full app (map + all tabs)
python -m vacationeer serve <trip.json>    # Build + FastAPI server + open browser
```

### Scheduling (planning module)
```bash
python -m vacationeer init-days <trip.json>                          # Create empty Day for each date in range
python -m vacationeer schedule <trip.json> <attraction_id> <date> [-t HH:MM]  # Schedule attraction onto a day
python -m vacationeer schedule-day-trip <trip.json> <day_trip_id> <date> [-d HH:MM]  # Expand day trip into activities
python -m vacationeer unschedule <trip.json> <activity_id>           # Remove activity from its day
python -m vacationeer backlog <trip.json>                            # Show unscheduled attractions & day trips
python -m vacationeer swap-days <trip.json> <date1> <date2>          # Swap activities between two days
python -m vacationeer move-activity <trip.json> <activity_id> <date> # Move activity to different day
```

---

## Feature Status

### Implemented
- [x] **Data models** — Trip, Attraction, Activity, Day, DayTrip, TravelSegment, Preferences with Pydantic
- [x] **Storage abstraction** — `TripStore` Protocol + `JsonTripStore` implementation (swappable for DB later)
- [x] **Planning module** — `planning/scheduler.py` with pure functions: init_days, schedule, schedule_day_trip, unschedule, get_unscheduled, swap_days, move_activity
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
- [x] **Sample data** — Valencia 2026 trip with 29 attractions + 3 day trips (with sub-attractions and travel segments)
- [x] **CLI** — map, info, build, serve + scheduling commands (init-days, schedule, schedule-day-trip, unschedule, backlog, swap-days, move-activity)

### Planned — Timeline (see docs/timeline-architecture.md)
- [ ] Proportional time-axis (1 min = 1.5px, variable-height blocks)
- [ ] Backlog sidebar (unscheduled attractions)
- [ ] Transit segments between activities (walking time via haversine)
- [ ] Free time gap visualization
- [ ] Day stats in headers (cost, walking distance, activity count)
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
pip install pydantic folium click fastapi uvicorn
python -m vacationeer serve trips/valencia-2026/trip.json
```

### Adding attractions
Edit `trips/valencia-2026/trip.json` — add entries to the `attractions` array following the existing format. All fields except `id`, `name`, `location`, and `category` are optional.

### Adding day trips
Add entries to the `day_trips` array. A day trip needs: `id`, `name`, `destination`, `location`, and at least one sub-attraction. Optionally add `outbound`/`return_trip` TravelSegments with transport details.

### Scheduling a day
```bash
python -m vacationeer init-days trips/valencia-2026/trip.json   # Creates empty days
python -m vacationeer schedule trips/valencia-2026/trip.json mercado-central 2026-03-21 -t 09:00
python -m vacationeer schedule-day-trip trips/valencia-2026/trip.json sagunto-day-trip 2026-03-22 -d 08:30
python -m vacationeer backlog trips/valencia-2026/trip.json     # See what's not scheduled yet
```

### Rebuilding
```bash
python -m vacationeer build trips/valencia-2026/trip.json
# Output: output/valencia-map.html + output/valencia-app.html
```

---

## Architecture Notes

### Storage layer
`TripStore` Protocol in `storage/base.py` defines `load()` / `save()`. Currently only `JsonTripStore` (JSON files) implements it. To add a database backend, implement the Protocol — no business logic changes needed.

### Planning module
All scheduling functions in `planning/scheduler.py` are **pure**: they take a Trip, mutate it, and return it. The caller is responsible for loading and saving via a store. This keeps planning logic framework-independent and testable.

### DayTrip → Activity expansion
When `schedule_day_trip()` is called, it expands a DayTrip into individual Activities on a Day:
1. Outbound travel activity (category=TRANSPORT)
2. One activity per sub-attraction
3. Return travel activity (category=TRANSPORT)

All generated activities carry `day_trip_id` so they can be traced back to the source DayTrip.

---

### For agents working on this project
- Read this file first for context
- Read `docs/timeline-architecture.md` for timeline-specific plans
- Models are in `vacationeer/models/trip.py` — always check current schema
- Storage abstraction: `storage/base.py` (Protocol) + `storage/json_store.py` (implementation)
- Planning logic: `planning/scheduler.py` — pure functions, no side effects
- Views generate HTML strings — all CSS/JS is inline (no external deps)
- Map uses Folium — tiles must work without Referer header (no OSM tiles)
- Color theme: navy #1a2332 + white, category colors listed above
- Test with: `python -m vacationeer build trips/valencia-2026/trip.json`
