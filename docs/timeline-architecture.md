# Timeline Feature Architecture Plan

## Current State
Static HTML generator with scheduling CLI. Trip has `attractions` (backlog), `day_trips` (composite entities with sub-attractions and travel segments), and `days` (each with `activities`). Activity model has `attraction_id`, `day_trip_id`, `start_time`, `duration_minutes`, `status`, `category` (denormalized), `travel_from_prev_minutes`. Valencia trip has 29 attractions + 3 day trips (Sagunto, Albufera, Xativa), each with sub-attractions and outbound/return TravelSegments.

### Already implemented
- Model additions (Activity: `category`, `travel_from_prev_minutes`, `day_trip_id`; Day: `start_time`)
- `DayTrip` model with `sub_attractions`, `outbound`/`return_trip` TravelSegments
- `TripStore` Protocol + `JsonTripStore` (storage abstraction)
- `planning/scheduler.py`: `init_days`, `schedule`, `schedule_day_trip`, `unschedule`, `get_unscheduled`, `swap_days`, `move_activity`
- CLI commands: `init-days`, `schedule`, `schedule-day-trip`, `unschedule`, `backlog`, `swap-days`, `move-activity`

---

## 1. Data Flow

### Scheduling attractions into days (3 modes)
1. **CLI** (first): `vacationeer schedule <attraction_id> <date> [--time HH:MM]`
2. **Drag from backlog** (Phase 2): JS drag-drop in timeline view, writes JSON patch back
3. **AI suggestion** (Phase 3): Chat sends attraction list + preferences to LLM, returns structured day plan

### Day structure: ordered list with optional times
Not rigid morning/afternoon/evening blocks — real travel days are fluid. If times are set, render a time axis; if not, render a simple sequence.

### Model additions (implemented)
```python
# Activity — added:
    category: Optional[Category] = None             # Denormalized for display
    travel_from_prev_minutes: Optional[int] = None   # Transit from previous
    day_trip_id: Optional[str] = None                # Links back to DayTrip source

# Day — added:
    start_time: Optional[time] = None   # Day start for layout

# New models:
    TravelSegment  # mode, origin, destination, times, price, booking_reference
    DayTrip        # destination, sub_attractions, outbound/return_trip TravelSegments
    TravelMode     # train, bus, car, walk, boat, metro
```

### Travel time
`travel_from_prev_minutes` on Activity. Compute via haversine distance with walking-speed heuristic (~5 km/h). Timeline renders thin "transit" bars between blocks.

### Meals & breaks
Just activities with `category = FOOD` and no `attraction_id`. Keeps model uniform.

---

## 2. Visual Design: Vertical Timeline with Proportional Time Axis

```
[Day Tab Bar]  Day 1 | Day 2 | Day 3 | ...

[Day Header]   Saturday, Mar 21 — "Old Town & Markets"
               Budget: €14 / €250 | Walking: ~4.2 km | 5 activities

[Time Axis]    [Activity Blocks]
 09:00 ----    +----------------------------------+
               | Mercado Central                  |
               | 09:00-10:00 | Free | food        |
               +----------------------------------+
               ~ 8 min walk ~
 10:08 ----    +----------------------------------+
               | La Lonja de la Seda              |
               | 10:08-10:53 | €2 | landmark      |
               +----------------------------------+
               ~ 3 min walk ~
 10:56 ----    +----------------------------------+
               | Valencia Cathedral               |
               | 10:56-12:11 | €10 | landmark     |
               +----------------------------------+
               ...
 12:30         [+ Add activity]
```

### Key elements
- **Scale**: 1 min = 1.5px (60-min activity = 90px, 10-hour day = 900px scrollable)
- **Activity blocks**: Height proportional to duration, min 60px. Category-tinted background
- **Transit segments**: Dashed connector + "8 min walk" label in muted gray
- **Free time gaps**: Striped area labeled "Free time (45 min)" — shows where to insert activities
- **Status dots**: green=done, blue=confirmed, yellow=planned, gray=skipped

### Map sync
`postMessage` between app shell and map iframe. Day tab click sends `{ type: "showDay", attractionIds: [...] }`. Map highlights markers and draws polyline route.

---

## 3. Day Management

### Unscheduled attractions (backlog) — implemented
`planning/scheduler.py:get_unscheduled(trip)` returns `(list[Attraction], list[DayTrip])` — both regular attractions and day trips not assigned to any day. Also available via `vacationeer backlog <trip.json>`.

### CLI commands — implemented
- `vacationeer init-days <trip.json>` — create empty Day for each date in range
- `vacationeer schedule <trip.json> <attraction_id> <date> [--time HH:MM]`
- `vacationeer schedule-day-trip <trip.json> <day_trip_id> <date> [--depart HH:MM]`
- `vacationeer unschedule <trip.json> <activity_id>`
- `vacationeer backlog <trip.json>` — show unscheduled attractions and day trips
- `vacationeer swap-days <trip.json> <date1> <date2>`
- `vacationeer move-activity <trip.json> <activity_id> <target_date>`

### CLI commands — planned
- `vacationeer auto-plan <trip.json>` — geographic clustering + ordering

### Auto-plan algorithm
1. Haversine distance matrix between all attractions
2. Greedy nearest-neighbor clustering, respecting daily time budget from `preferences.pace`
3. Order within cluster to minimize walking (nearest-neighbor TSP)
4. Assign clusters to dates, highest-score attractions earlier

Place in `vacationeer/planning/scheduler.py`.

---

## 4. Interactive Features (architect now)

### JSON patch approach for interactivity
1. Embed trip data as `<script>const TRIP_DATA = {...};</script>`
2. JS operations modify in-memory object
3. "Save" button downloads JSON or POSTs to local server

### Drag and drop
HTML5 DnD API with `draggable="true"`. ~80 lines vanilla JS.

### Click to edit
Inline edit form replacing card content: time input, duration input, notes text.

### Daily stats
Sum prices, compute walking distance (haversine between consecutive), compare against budget.

---

## 5. Implementation Sequence

1. ~~Extract shared helpers (`views/colors.py`, `views/helpers.py`)~~
2. ~~Add model fields to Activity and Day~~ — done: category, travel_from_prev_minutes, day_trip_id, start_time
3. ~~`init-days` CLI command~~ — done
4. ~~`schedule` CLI command~~ — done (+ schedule-day-trip, unschedule, backlog, swap-days, move-activity)
5. Rewrite `render_timeline` with proportional time-axis
6. Backlog rendering in timeline
7. Day stats (cost, distance) in headers
8. `auto-plan` in `planning/scheduler.py`
9. Map sync via postMessage
10. Embedded JSON + interactive JS (drag-drop, inline edit)

### Framework migration trigger
When you need real-time bidirectional state (chat working, collaborative editing). Then: FastAPI backend + lightweight frontend framework. All planning logic in `scheduler.py` is framework-independent.
