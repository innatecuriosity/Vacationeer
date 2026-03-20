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
- Android: PWA (implemented), native wrapper via Capacitor if needed
- Backend: FastAPI for real-time features (chat, sync)
- AI: Claude API for chat-based editing and auto-planning

---

## Project Structure

```
VacationeerPoc/
├── vacationeer/
│   ├── __main__.py          # CLI: all commands (build, plan, pipeline, sync)
│   ├── theme.py             # Centralized colors, fonts, category metadata (single source of truth)
│   ├── utils.py             # Shared utilities (slugify, etc.)
│   ├── pwa.py               # PWA asset generation (manifest, service worker, icon)
│   ├── models/
│   │   ├── __init__.py      # Exports all models
│   │   └── trip.py          # Pydantic models (see Core Entities below)
│   ├── storage/
│   │   ├── base.py          # TripStore Protocol (abstract interface)
│   │   └── json_store.py    # JsonTripStore implementation
│   ├── planning/
│   │   └── scheduler.py     # Pure scheduling functions (init_days, schedule, etc.)
│   ├── pipeline/             # New trip creation pipeline
│   │   ├── ai_provider.py   # AIProvider ABC + 3 implementations (cascade)
│   │   ├── questionnaire.py # Interactive Click-based trip setup
│   │   ├── templates.py     # Research + conversion prompt templates
│   │   ├── research.py      # AI-driven destination research → 3 MD files
│   │   ├── converter.py     # AI-driven MD → trip.json conversion
│   │   └── runner.py        # Background pipeline runner (daemon threads + job tracking)
│   ├── sync/                 # MD ↔ JSON sync (marker-based)
│   │   ├── markers.py       # @vacationeer marker block format
│   │   ├── md_parser.py     # Extract structured data from MD markers
│   │   ├── md_writer.py     # Inject/update markers in MD files
│   │   └── sync_engine.py   # Compare MD vs JSON, produce diffs
│   ├── maps/
│   │   └── generator.py     # Folium map generation
│   └── views/
│       ├── __init__.py
│       ├── helpers.py       # Shared view utilities (esc, format_price, format_time, etc.)
│       ├── app_shell.py     # Main HTML shell with sidebar
│       ├── overview.py      # Attractions overview tab
│       ├── timeline.py      # Daily timeline tab
│       └── chat.py          # (legacy) Chat bubble renderer, unused — chat is now in sidebar
├── tests/                    # Automated tests (pytest)
│   ├── test_theme.py        # Theme constants and category metadata
│   ├── test_helpers.py      # View helper functions
│   ├── test_utils.py        # Utility functions (slugify)
│   └── test_models.py       # Pydantic model behavior (dest_slug, defaults)
├── trips/
│   └── valencia-2026/
│       ├── trip-config.json  # Pipeline questionnaire output
│       └── trip.json         # Trip data (29 attractions + 3 day trips)
├── data/
│   └── valencia-2026/       # Source markdown research files
├── docs/
│   ├── PROJECT.md           # This file
│   ├── GITHUB_PAGES.md      # GitHub Pages deployment guide
│   └── timeline-architecture.md
├── export/                   # PWA export output (for GitHub Pages deployment)
├── .active-trip              # Currently selected trip slug
└── output/                   # Generated HTML files
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

### Grouping
A named, hierarchical collection of attractions. Lives on `trip.groupings`. Fields:
- `id`, `name`, `description`, `color` — display metadata (color auto-assigned from palette)
- `parent_id` — optional parent grouping for hierarchy (flat list with parent pointers)
- `member_ids` — list of attraction IDs belonging to this grouping

An attraction can belong to multiple groupings. Hierarchy is validated for cycles (max 10 levels). Recursive member collection gathers IDs from all descendants.

### Itinerary
A named arrangement of days for the trip. Multiple itineraries allow comparing alternative schedules (e.g. "Itinerary A" with museums early vs "Itinerary B" with food focus). Fields:
- `id`, `name`, `description` — identification and notes
- `days: list[Day]` — the schedule for this itinerary

Only one itinerary is active at a time (`trip.active_itinerary_id`). All scheduling operations (drag-and-drop, API endpoints, chat actions) operate on the active itinerary. Attractions and day trips are shared across itineraries — only their scheduling differs.

**Auto-migration**: Existing trip.json files with a top-level `days` array are automatically migrated to `itineraries[0]` on load via a Pydantic `model_validator`.

### Trip
Top-level container: destination, dates, travelers, budget, preferences, `attractions` (backlog of regular places), `day_trips` (composite day trip entities), `itineraries` (named schedule variants), `active_itinerary_id`, `groupings` (hierarchical attraction collections). Legacy `days` field is auto-migrated to itineraries.

### Preferences
User's interests, things to avoid, pace (relaxed/moderate/packed), daily budget.

### Categories
landmark, museum, nature, food, entertainment, transport, accommodation, shopping, day_trip, infrastructure

### TravelMode
train, bus, car, walk, boat, metro

---

## CLI Commands

### Trip Management
```bash
python -m vacationeer trips                # List all trips, show active (*) and status
python -m vacationeer use <slug>           # Set active trip (e.g. 'valencia-2026')
```

The active trip is stored in `.active-trip`. Pipeline commands (`gen-research`, `import-trip`) default to the active trip's config when no path is given.

### Pipeline — New Trip Creation
```bash
python -m vacationeer new-trip                              # Interactive questionnaire → trip-config.json
python -m vacationeer gen-research [config.json]            # AI generates 3 MD research files (default: --light)
python -m vacationeer gen-research --no-light [config.json] # Full research (more attractions, detailed)
python -m vacationeer import-trip [config.json]             # AI converts MD files → trip.json
python -m vacationeer import-trip [config.json] --json-input <file>  # Validate + save pre-made JSON
```

**AI provider cascade** (automatic): Claude Code CLI → Anthropic API → manual prompt file.
Override with `--provider claude-code|api|manual`.

**Light mode** (`--light`, default ON): Produces ~5-6 attractions + 2 day trips for quick testing.
Use `--no-light` for comprehensive research.

### Sync — MD ↔ JSON
```bash
python -m vacationeer inject-markers <trip.json>  # One-time: add @vacationeer markers to MD files
python -m vacationeer sync-status <trip.json>     # Show diffs between MD markers and JSON
python -m vacationeer sync-to-md <trip.json>      # JSON → MD: update markers from JSON values
python -m vacationeer sync-from-md <trip.json>    # MD → JSON: update JSON from marker values
```

### Build, Serve & Export
```bash
python -m vacationeer map <trip.json>      # Generate map HTML only
python -m vacationeer info <trip.json>     # Show trip summary
python -m vacationeer build <trip.json>    # Generate full app (map + all tabs)
python -m vacationeer serve <trip.json>    # Build + FastAPI server + open browser
python -m vacationeer export <trip.json>   # Export as PWA folder for GitHub Pages
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
  - Emoji DivIcons for ALL categories (landmark 🏛, museum 🖼, nature 🌳, food 🍽, entertainment 🎭, transport 🚌, accommodation 🏨, shopping 🛍, day_trip 🌍, infrastructure ✈)
  - Name labels below each emoji (toggleable via Labels checkbox control)
  - MarkerCluster for decluttering at low zoom (custom styled, dissolves at zoom 15+)
  - Outlier-filtered centering (ignores 0,0 and far-flung points via median filter)
  - Rich hover tooltips (name, category, description preview, duration/price/score)
  - Inline popup editing: clickable star rating (1-10), edit duration/price, save via API
  - Map ↔ app sync: popup edits trigger store reload via postMessage
  - Custom Leaflet layer control: collapsible toggle button (hidden by default), collapsible sections (Categories open, Groupings collapsed), all/none toggles, colored dots for groupings, Labels toggle
  - Mobile-friendly map popups (`max-width: 85vw`), bigger touch targets for layer checkboxes on mobile
  - Grouping polygon overlays: convex hull (≥3 members), polyline (2), circle (1) per grouping, togglable via layer control
  - Auto-refresh after mutations (cache-busting iframe reload)
- [x] **App shell** — Single HTML page with:
  - Dark navy (#1a2332) sidebar (340px) with Map/Overview/Timeline tabs
  - Always-visible chat panel in sidebar (below nav, dark-themed)
  - Mobile responsive: sidebar becomes slide-out drawer with hamburger button + overlay backdrop, auto-closes on nav tap
  - Modals go fullscreen on mobile, form rows stack vertically, toasts span full width
  - Trip header with metadata
  - Trip picker dropdown (switch between trips, shows pipeline status for in-progress trips)
  - New Trip modal with form + real-time progress tracking (Alpine.js)
  - 3-mode location picker (Address / GPS / Pick on Map with Leaflet mini-map using CartoDB Voyager tiles) in all location modals
- [x] **Overview tab** — Attractions sorted by category (default):
  - Rounded rectangle cards (8px radius, 1px border, 6px colored left border per category)
  - Two-row collapsed header: name + description preview + chevron; category pill + score bar + duration + price
  - Expandable cards (click to reveal full details, inline editing, star rating)
  - Score bars (green 8+, yellow 6-8, red <6)
  - Tags as pills, tips box, URL buttons
  - Search and filter by category, sort by name/category/score/price
  - Grouping pills on card headers (colored, from groupings the attraction belongs to)
  - Filter by grouping (dropdown alongside category filter)
  - Expanded card: groupings section with toggle checkboxes for quick add/remove
  - Mobile responsive: summary/filters/search shrink padding, edit form stacks vertically
- [x] **Timeline tab** — Kanban-style board with drag-and-drop:
  - Left sidebar: unscheduled attractions pool (with day trips section)
  - Horizontal scrolling day columns — all days visible at once
  - SortableJS drag-and-drop: pool → day (schedule), day → pool (unschedule), day → day (move), within day (reorder)
  - Day column headers: Day N, weekday + date (Mon, Jul 6), editable label; swap buttons (← →) to reorder days
  - Inline editing: click day label or notes to edit in-place (PATCH /api/days/{date})
  - Activity cards: time, name, description, duration, notes; proportional min-height based on duration
  - Pool cards show description/english name below attraction name, with grouping pills
  - Click-to-expand detail modal: full attraction info (description, tips, 10-star rating, duration, price, address, Google Maps link, URL, tags, scheduled day/time, day-trip sub-attractions); actions: unschedule, delete
  - Card buttons: ▼ expand + × remove, 28px desktop / 36px mobile touch targets
  - Whole card is draggable (no handle restriction), `user-select: none` prevents text selection; buttons excluded via SortableJS `filter`
  - Footer stats per day: total hours, cost, item count
  - Alpine.js `kanbanTimeline()` component reads from `$store.trip`, syncs via API after each drag
  - SortableJS freeze fix: dragged DOM elements removed before Alpine re-render to prevent conflicts
  - Mobile responsive: pool stacks on top, columns full-width vertical stacking, bigger touch targets (36px buttons), itinerary bar horizontal scroll, detail modal fullscreen, 480px small-phone breakpoint
- [x] **Sidebar chat** — Always-visible AI assistant panel in sidebar:
  - Dark-themed message bubbles with **markdown rendering** (via marked.js)
  - Connected via `POST /api/chat` using AI provider cascade (Claude Code CLI → Anthropic API)
  - No API key needed when Claude Code CLI is installed locally
  - **Slim system prompt** with on-demand data access via tool-use loop
  - **Data tools**: AI requests trip data via tags (`<<GET_ATTRACTIONS>>`, `<<GET_SCHEDULE>>`, `<<GET_DAY_TRIPS>>`, `<<GET_UNSCHEDULED>>`), server resolves and re-sends (max 2 rounds)
  - **Action tools**: AI executes trip modifications via tags (`<<SCHEDULE:name:date:time>>`, `<<UNSCHEDULE:name:date>>`), server resolves names to IDs, executes, and returns `trip_changed` flag
  - Frontend auto-reloads store when `trip_changed: true` — timeline/map update immediately
  - **Client-side skills**: `/add`, `/list`, `/unscheduled`, `/days`, `/schedule`, `/day`, `/help`
  - `/add <name>` uses dedicated `POST /api/chat/add` endpoint for AI-powered attraction research
  - Chat history persists across refreshes via `localStorage`
  - Clear chat button in header
  - Alpine.js `sidebarChat()` component with message history, persistence, and auto-scroll
- [x] **Groupings** — Hierarchical attraction collections:
  - Data model: `Grouping` with `parent_id` hierarchy + `member_ids` many-to-many
  - Server CRUD: 6 endpoints (`GET/POST/PATCH/DELETE /api/groupings`, member add/remove)
  - Cycle detection on parent assignment (max 10 levels)
  - Auto-color from palette (`theme.py: GROUPING_PALETTE`)
  - Overview: colored pills on cards, filter by grouping, toggle checkboxes in expanded cards
  - Timeline: grouping pills on pool cards
  - Map: convex hull polygons per grouping (pure Python Andrew's monotone chain), togglable layers
  - Custom Leaflet layer control: Categories + Groupings sections with all/none toggles, no radio buttons
  - Management modal: create/edit/delete groupings, color picker, parent selector, member checkboxes
  - Alpine store methods: `addGrouping`, `updateGrouping`, `deleteGrouping`, `toggleGroupingMember`, `getGroupingsForAttraction`, `getAllMemberIds`
- [x] **Multiple itineraries** — Named schedule variants (A/B/C) for comparing alternatives:
  - Data model: `Itinerary` with `id`, `name`, `description`, `days`; `Trip` has `itineraries` list + `active_itinerary_id`
  - Auto-migration: legacy `trip.days` → `itineraries[0]` via Pydantic `model_validator`
  - Server CRUD: 6 endpoints (`GET/POST /api/itineraries`, `PATCH/DELETE /api/itineraries/{id}`, activate, clone)
  - New itineraries start with empty days for the full trip date range; cloning deep-copies all activities
  - Itinerary switcher bar on timeline: pill tabs with scheduled/total count badges, dots menu (edit/duplicate/delete), "+ New" button
  - Inline editing: name + description editable from the switcher bar
  - Comparison panel: toggle to see side-by-side summary stats (scheduled count, total hours, cost, busiest/emptiest day) + day-by-day grid with activity pills
  - All scheduling operations (drag-and-drop, API, chat) operate on the active itinerary
  - Attractions and day trips are shared — only their scheduling per itinerary differs
  - SortableJS reinits on itinerary switch via `$watch`
  - Alpine store methods: `switchItinerary`, `createItinerary`, `updateItinerary`, `deleteItinerary`, `cloneItinerary`
- [x] **Sample data** — Valencia 2026 trip with 78 attractions + 8 day trips + 18 groupings (neighbourhoods: City Center, El Carmen, Ruzafa, Cabanyal, Waterfront; themes: Street Art, Hidden Gardens, Architecture, Turia Corridor; activities: Coffee & Brunch, Tapas, Drinks, Sunset Spots, Museums, Fun & Games, Hidden Gems, Free Activities, City of Arts & Sciences)
- [x] **CLI** — map, info, build, serve + scheduling commands (init-days, schedule, schedule-day-trip, unschedule, backlog, swap-days, move-activity)
- [x] **Trip management** — `trips` (list with status), `use` (set active trip), `.active-trip` file
- [x] **Pipeline** — New trip creation flow:
  - Interactive questionnaire (`new-trip`) → `trip-config.json`
  - AI research generation (`gen-research`) → 3 MD files (attractions, day trips, good-to-know)
  - AI-driven MD → JSON conversion (`import-trip`) → `trip.json`
  - Light mode (default) for fast testing, `--no-light` for full research
  - Background execution via daemon threads — user can browse other trips while AI works
  - **Instant trip creation**: skeleton trip.json + placeholder map + app HTML built synchronously in `start_pipeline()` before thread launches — trip is navigable immediately
  - Frontend auto-navigates to the new trip page after submit (no progress modal)
  - Pipeline progress banner on trip page: polls `/api/pipeline/status/{slug}` every 3s, auto-reloads when done
  - Trip picker shows pulsing `⏳` indicator for in-progress pipeline trips
  - REST API: `POST /api/pipeline/start`, `GET /api/pipeline/status/{slug}`, `GET /api/pipeline/jobs`
- [x] **AI provider abstraction** — `AIProvider` ABC with cascade:
  - `ClaudeCodeProvider` — invokes `claude` CLI subprocess (preferred, uses logged-in session); Windows-compatible (shell=True + shutil.which + UTF-8 encoding + stdin prompt)
  - `ClaudeAPIProvider` — uses `anthropic` SDK (needs `ANTHROPIC_API_KEY`)
  - `ManualProvider` — writes prompt files for user to paste into Claude
- [x] **MD ↔ JSON sync** — Bidirectional sync via `@vacationeer` marker blocks:
  - `inject-markers` — one-time injection of structured data blocks into MD files
  - `sync-status` — dry-run diff between MD markers and JSON
  - `sync-to-md` / `sync-from-md` — apply changes in either direction

### Planned — Timeline (see docs/timeline-architecture.md)
- [x] Backlog sidebar (unscheduled attractions pool with drag-and-drop)
- [x] Kanban board with all days visible as columns
- [x] Day swap/reorder via ← → buttons (POST /api/days/swap)
- [x] Move activities between days via drag-and-drop (POST /api/activities/move)
- [x] Inline editing of day label and notes
- [x] Day stats in footers (hours, cost, item count)
- [x] Duration-proportional card heights
- [ ] AI day planning: auto-fill day from description (POST /api/days/{date}/ai-plan, endpoint ready)
- [ ] Transit segments between activities (walking time via haversine)
- [ ] CLI: `auto-plan` (geographic clustering + nearest-neighbor TSP)
- [ ] Map sync via postMessage (highlight day's attractions + route polyline)

### Planned — Interactive Features
- [x] Embed trip data as JSON in HTML for client-side editing (Alpine.js `$store.trip`)
- [x] CRUD modals: Attraction, Accommodation, Transport, Day Trip, Day (FAB menu)
- [x] Context-aware FAB: full menu on Map/Overview, direct "Add Day" on Timeline
- [x] Location picker with 3 modes (Address, GPS, Pick on Map) in all location modals
- [x] Modal resilience (`@mousedown.self` prevents close on paste/drag)
- [x] Drag-and-drop reordering of activities within a day (SortableJS)
- [x] Drag attractions from unscheduled pool into days
- [x] Inline editing in map popups (duration, price, star rating)
- [x] Click-to-expand detail modal on timeline cards (full info, links, rating, actions)
- [ ] Click-to-edit time/duration/notes in timeline

### Planned — Chat / AI
- [x] Connect chat to AI provider cascade (sidebar panel, `POST /api/chat`, CLI preferred)
- [x] Tool-use loop: AI requests data via `<<GET_*>>` tags, server resolves and re-sends; AI executes actions via `<<SCHEDULE:..>>` / `<<UNSCHEDULE:..>>` tags, server resolves names→IDs and modifies trip
- [x] "Add attraction" via `/add` chat skill (AI researches via `POST /api/chat/add`, returns structured JSON with coordinates, price, duration, tips)
- [x] "Schedule attraction" via chat — AI outputs action tag, server executes, frontend reloads
- [x] "Unschedule attraction" via chat action tag
- [x] Chat persistence via localStorage (survives page refreshes)
- [x] Markdown rendering in chat (marked.js)
- [x] Client-side skills: `/list`, `/unscheduled`, `/days`, `/schedule`, `/day`, `/help`
- [ ] AI-suggested day plans based on preferences + proximity
- [ ] "Reorganize day" via chat
- [ ] Streaming responses (SSE) for better UX
- [ ] Edit/delete attractions via chat actions

### Planned — Scoring & Filtering
- [ ] Map filtering by score range
- [ ] Map filtering by user_score vs expected_score
- [ ] Auto-compute expected_score from preferences (keyword matching)
- [x] User score input UI (clickable 1-10 star rating in map popup)

### Planned — Data & Content
- [ ] Attraction image scraping (from URLs or search)
- [ ] Weather data integration for date-based planning
- [ ] Opening hours / seasonal availability
- [ ] Price currency conversion

### Implemented — Mobile / Offline
- [x] **PWA export** — `export` CLI command produces self-contained folder with manifest, service worker, SVG icon
- [x] **Offline editing** — all mutations fall back to localStorage when server is unavailable
- [x] **Export/Import** — download/upload trip JSON from the app UI for syncing between devices
- [x] **GitHub Pages deployment** — see `docs/GITHUB_PAGES.md` for setup instructions
- [x] **Installable on Android** — add to home screen from Chrome, runs as standalone app

### Planned — Mobile / Offline (future)
- [ ] Offline map tile caching
- [ ] Automatic sync between devices

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
infrastructure:#34495E
```

---

## Working with This Project

### Quick start — existing trip
```bash
cd VacationeerPoc
pip install pydantic folium click fastapi uvicorn
python -m vacationeer use valencia-2026
python -m vacationeer serve trips/valencia-2026/trip.json
```

### Quick start — new trip
```bash
python -m vacationeer new-trip              # Answer questionnaire, auto-sets active trip
python -m vacationeer gen-research          # AI generates research (light mode by default)
# Review/edit the MD files in data/<slug>/
python -m vacationeer import-trip           # AI converts MD → trip.json
python -m vacationeer serve trips/<slug>/trip.json
```

### Adding attractions
Edit `trips/<slug>/trip.json` — add entries to the `attractions` array following the existing format. All fields except `id`, `name`, `location`, and `category` are optional.

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
All scheduling functions in `planning/scheduler.py` are **pure**: they take a Trip, mutate it, and return it. The caller is responsible for loading and saving via a store. This keeps planning logic framework-independent and testable. All scheduler functions operate on the **active itinerary's** days via the `_itin_days(trip)` helper (returns a mutable reference to `trip.active_itinerary.days`).

### DayTrip → Activity expansion
When `schedule_day_trip()` is called, it expands a DayTrip into individual Activities on a Day:
1. Outbound travel activity (category=TRANSPORT)
2. One activity per sub-attraction
3. Return travel activity (category=TRANSPORT)

All generated activities carry `day_trip_id` so they can be traced back to the source DayTrip.

---

### Pipeline module
The `pipeline/` module handles new trip creation. The AI provider abstraction (`ai_provider.py`) defines a cascade: Claude Code CLI → Anthropic API → manual prompt file. All AI-dependent steps (research generation, MD→JSON conversion) go through this interface. The `--light` flag (default ON) prefixes the research prompt with instructions to produce minimal output for faster iteration.

Background execution is handled by `pipeline/runner.py`: `start_pipeline()` first creates a **skeleton trip** synchronously (empty trip.json + placeholder map + app HTML via `_build_skeleton()`), then launches a daemon thread that runs research → conversion → HTML build, tracking progress in a `PipelineJob` dataclass. This means the trip is navigable immediately — the user can browse the empty trip page while AI works in the background. The server exposes pipeline status via REST endpoints (`/api/pipeline/start`, `/api/pipeline/status/{slug}`, `/api/pipeline/jobs`). The frontend auto-navigates to the new trip after creation. A `pipelineBanner()` Alpine component on the trip page polls status every 3 seconds and auto-reloads when the pipeline completes. The trip picker shows a pulsing indicator for in-progress trips.

### Sidebar chat
The chat assistant lives in the sidebar (always visible alongside map/overview/timeline). The Alpine.js `sidebarChat()` component sends messages to `POST /api/chat`, which uses the AI provider cascade (`get_provider()` from `pipeline/ai_provider.py`): Claude Code CLI first, then Anthropic API.

**System prompt**: Slim — only trip basics (name, dates, travelers) + tool descriptions. Trip data (attractions, schedule, day trips) is NOT embedded; the AI requests it on demand via data tool tags.

**Data tools (read-only)**: The AI outputs `<<GET_ATTRACTIONS>>`, `<<GET_SCHEDULE>>`, `<<GET_DAY_TRIPS>>`, or `<<GET_UNSCHEDULED>>` tags. The server detects these, resolves them into formatted trip data, and re-sends the full conversation with the data appended (max 2 rounds). This avoids bloating the system prompt while giving the AI access to all trip information.

**Action tools (modify trip)**: The AI outputs `<<SCHEDULE:name:YYYY-MM-DD:HH:MM>>` or `<<UNSCHEDULE:name:YYYY-MM-DD>>` tags. The server fuzzy-matches attraction names to IDs (`_find_attraction_by_name()`), executes the action (create/modify Day, add/remove Activity), saves trip, rebuilds HTML. Action tags are stripped from the response text. The server returns `trip_changed: true` so the frontend can reload the store.

**Client-side skills**: Chat input starting with `/` is handled client-side without AI. Skills: `/add <name>` (AI research + add via `POST /api/chat/add`), `/list`, `/unscheduled`, `/days`, `/schedule <id> <date> [time]`, `/day <date> [label]`, `/help`.

**Markdown**: Assistant messages are rendered via marked.js (`renderMd()` method). User messages stay plain text.

**Persistence**: Chat messages persist to `localStorage` (key: `vacationeer_chat`). A "Clear" button resets to the default greeting. Messages survive page refreshes and `$store.trip.reload()` calls after actions.

**Windows compatibility**: `ClaudeCodeProvider` uses `shell=True` on Windows (npm installs `.cmd` wrappers), resolves the binary via `shutil.which()`. System prompt is prepended to stdin inside `<instructions>` tags (avoids Windows CLI argument length/escaping issues with `--system-prompt` flag). Forces `encoding="utf-8"` for non-ASCII characters.

**Layout**: Export/Import buttons are in the trip picker dropdown (not sidebar bottom). Nav tabs use `flex-shrink: 0` so chat fills all remaining sidebar space.

### Sync module
The `sync/` module enables bidirectional sync between MD research files and `trip.json`. It uses `@vacationeer` marker blocks (HTML comments with key-value data) injected below attraction headings in MD files. The sync engine compares marker values against JSON fields and can apply updates in either direction.

### PWA & offline editing
The app works in two modes:
- **Server mode** (`vacationeer serve`): all mutations go through FastAPI endpoints, data persisted to `trip.json` on disk
- **Offline mode** (exported PWA or when server is unreachable): mutations fall back to `localStorage`, data persists in the browser

The offline layer (`offlineFetch()` in `app_shell.py`) wraps every Alpine store method: try server first, on network error apply the mutation locally and save to `localStorage['vacationeer_trip_<id>']`. On page load, localStorage state is merged with embedded `__TRIP_DATA__`.

The `export` command (`pwa.py`) generates a PWA folder with manifest.json, service worker (cache-first for CDN assets), SVG icon, and index redirect. Deploy to GitHub Pages for HTTPS + installability on Android. See `docs/GITHUB_PAGES.md`.

AI features (chat, day planning, new trip pipeline) require the server and are gracefully disabled offline.

### Theme & shared utilities
- `theme.py` is the **single source of truth** for all colors, fonts, and category metadata (color, folium_color, icon, emoji, label). Views and maps import from here — never hardcode category colors.
- `views/helpers.py` has shared view functions: `esc()` (HTML escaping), `format_price()`, `format_time()`, `format_duration()`, `category_label()`.
- `utils.py` has general utilities like `slugify()`.
- `Trip.dest_slug` property returns a URL-friendly slug derived from the destination name (used for output filenames).

### Mobile responsiveness
Three breakpoints: default (desktop), 768px (tablet), 480px (small phone). Key patterns:
- Sidebar: slide-out drawer with hamburger button + overlay on mobile (not collapsed strip)
- Map layer control: hidden behind toggle button, collapsible sections inside
- Kanban: columns go full-width and stack vertically on mobile
- Modals/detail panels: fullscreen on mobile
- Touch targets: minimum 36px on mobile (buttons, checkboxes)
- Overview: filter bars, search, edit forms all have mobile-specific sizing

### Tests
Tests live in `tests/` and use pytest. Run with `python -m pytest tests/ -v`. Currently covers theme constants, view helpers, utility functions, and model behavior.

### For agents working on this project
- Read this file first for context
- Read `docs/timeline-architecture.md` for timeline-specific plans
- Models are in `vacationeer/models/trip.py` — always check current schema
- **Theme/colors**: `vacationeer/theme.py` — never hardcode colors, import from here
- **View helpers**: `vacationeer/views/helpers.py` — use `esc()`, `format_price()`, etc.
- Storage abstraction: `storage/base.py` (Protocol) + `storage/json_store.py` (implementation)
- Planning logic: `planning/scheduler.py` — pure functions, no side effects
- Pipeline: `pipeline/` — AI provider cascade, questionnaire, research, conversion
- Sync: `sync/` — MD ↔ JSON bidirectional sync via marker blocks
- Views generate HTML strings — all CSS/JS is inline (CDN deps: Alpine.js, Leaflet, SortableJS)
- Chat is in the sidebar (not a tab) — `sidebarChat()` Alpine component, `POST /api/chat` backend
- Chat tool-use: AI outputs `<<GET_*>>` for data, `<<SCHEDULE:..>>` / `<<UNSCHEDULE:..>>` for actions — server resolves tags and re-sends or executes
- Chat uses marked.js for markdown rendering; system prompt delivered via stdin `<instructions>` tags (not `--system-prompt` CLI flag)
- In plain JS functions (not Alpine templates), use `Alpine.store('trip')` not `$store.trip`
- **Object.assign pitfall**: `Object.assign({}, src, { get foo() {...} })` evaluates getters once and copies the static result. Use regular methods or compute inline from `$store.trip` in Alpine components instead of relying on getters in the store.
- **Itineraries**: All day/activity endpoints use `_active_itin().days` (not `trip.days`). The `_active_itin()` helper resolves the current itinerary. Scheduler uses `_itin_days(trip)` for the same purpose.
- Map uses Folium — tiles must work without Referer header (no OSM tiles)
- Map CSS: inject via `folium.Element` into `get_root().html`, NOT via `MacroElement` (Jinja2 header macro doesn't render reliably for CSS)
- Map custom controls: inject via `MacroElement` with Jinja2 `{% macro script %}` template — renders in the script section AFTER Folium's map/layer initialization (unlike `folium.Element` which renders in `<body>` before map init)
- Groupings: `trip.groupings` list, CRUD via `/api/groupings/*`, convex hull polygons on map, pills on cards
- Color theme: navy #1a2332 + white, category colors in `theme.py`
- Test with: `python -m vacationeer build trips/valencia-2026/trip.json`
- Run tests: `python -m pytest tests/ -v`
