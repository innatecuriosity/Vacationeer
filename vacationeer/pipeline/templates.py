"""Prompt templates for the trip creation pipeline."""

LIGHT_RESEARCH_PREFIX = """\
**IMPORTANT: LIGHT MODE — This is a quick test run. Keep output minimal:**
- attractions-and-activities.md: Include only 5-6 top attractions (the absolute must-sees). \
Skip combo deals, cost estimates, and detailed zone descriptions. Keep each entry to ~3-5 lines \
plus the practical info table and Location/Score lines.
- day-trips.md: Include only 2 day trips with 2-3 sub-attractions each. Keep descriptions brief.
- good-to-know.md: Include only airport transfer, transport basics, and 3 food tips. Skip phrases, \
neighborhoods, cycling, and safety sections.

The format, Location/Score lines, and `<!-- @vacationeer -->` blocks must still be exactly the same — just less content.

---

"""

RESEARCH_SYSTEM = """\
You are an expert travel researcher. You produce detailed, practical, opinionated \
travel guides with accurate prices, GPS coordinates, and insider tips. \
Your output is richly formatted markdown designed for human reading and later \
machine conversion to structured data."""

RESEARCH_PROMPT = """\
# Research Task: {destination}

## Trip Details
- **Destination:** {destination}
- **Dates:** {date_description}
- **Travelers:** {travelers}
- **Budget:** {budget_description}
- **Interests:** {interests}
- **Pace:** {pace}
{optional_sections}

## Your Task

Research **{destination}** thoroughly and produce **THREE separate markdown files**. \
Output them clearly separated with these exact markers:

```
===FILE: attractions-and-activities.md===
(content)
===FILE: day-trips.md===
(content)
===FILE: good-to-know.md===
(content)
```

---

## File 1: attractions-and-activities.md

Structure:
```
# {{Destination}} - Attractions & Activities

**Trip:** {{dates}} | {{travelers description}} | {{budget description}}
**Context:** {{any special context}}

---

## THE BIG TICKET / COMBO DEALS
(Table comparing package deals vs individual prices. Include booking URLs.)

## MUST-DO: {{ATTRACTION NAME}}
*Duration | Area*

Detailed description with zones/highlights.

### Practical Info
| | |
|---|---|
| **Price** | ... |
| **Hours** | ... |
| **Time needed** | ... |
| **Best time** | ... |

> Location: {{lat}}, {{lng}} | {{address}}

### Pro Tips
- Tip 1
- Tip 2

<!-- @vacationeer
id: {{kebab-case-id}}
name: {{ATTRACTION NAME}}
type: attraction
price_eur: {{number or null}}
duration_minutes: {{number}}
location: {{lat}}, {{lng}} | {{address}}
expected_score: {{N}}
tips: {{one-line tip or null}}
url: {{booking/info url or null}}
-->

(Repeat for each major attraction)

## CATEGORY SECTION (e.g. LANDMARKS & ARCHITECTURE)

### {{Attraction Name}}
Description...

| | |
|---|---|
| **Price** | ... |
| **Hours** | ... |
| **Time needed** | ... |

> Location: {{lat}}, {{lng}} | {{address}}
> Score: {{N}}/10

<!-- @vacationeer
id: {{kebab-case-id}}
name: {{Attraction Name}}
type: attraction
price_eur: {{number or null}}
duration_minutes: {{number}}
location: {{lat}}, {{lng}} | {{address}}
expected_score: {{N}}
tips: {{one-line tip or null}}
url: {{url or null}}
-->

(Repeat)

## SUGGESTED DAY GROUPINGS
- **Group A:** ... (theme + which attractions pair well + why)
- **Group B:** ...

## COST ESTIMATE
| Item | Cost per person |
|---|---|
| ... | ... |
| **Total** | **...** |
```

Requirements:
- Include **every notable attraction** suitable for the stated interests
- Every attraction MUST have a `> Location: lat, lng | address` line with GPS coordinates
- Include pricing in EUR (or local currency with EUR equivalent)
- Include duration estimates in minutes/hours
- Include opening hours and best times to visit
- Include URLs for booking/info where available
- Suggest an expected_score (1-10) based on how well each matches the stated interests. \
Add it as: `> Score: 8/10`
- Include combo/package deals if they exist
- Group by category: landmarks, museums, nature, food, entertainment, shopping
- End with suggested day groupings and cost estimate
- Every attraction MUST have a `<!-- @vacationeer ... -->` HTML comment block (see template above). \
Use kebab-case IDs derived from the name (e.g. "valencia-cathedral", "mercado-central"). \
The block is invisible in markdown renderers and enables machine sync.

---

## File 2: day-trips.md

{day_trips_section}

---

## File 3: good-to-know.md

Structure:
```
# {{Destination}} - Good to Know

**Trip:** {{dates}}

---

## GETTING FROM THE AIRPORT
(Table: Option | Time | Cost | Notes)

## PUBLIC TRANSPORT
(Local transport options, best tickets, tourist cards with value analysis)

## CYCLING / WALKING
(Bike share systems, walking distances, terrain)

## WEATHER
(Expected weather for travel dates, what to pack)

## FOOD & EATING
(Meal costs, local specialties, meal times, tipping, best areas, budget tips)

## USEFUL PHRASES
(Table: English | Local language | Pronunciation)

## MONEY-SAVING TIPS
(Numbered list of practical tips)

## SAFETY & PRACTICAL
(Emergency numbers, scams to avoid, pharmacy info, water safety)

## NEIGHBORHOODS / AREAS
(Brief guide to main areas relevant for tourists)
```

Requirements:
- Focus on practical, actionable information
- Include current prices (as of {current_year})
- Tailor to the stated interests, budget, and travel context
- Include local customs and etiquette
"""

DAY_TRIPS_SECTION = """\
Structure:
```
# {{Destination}} - Day Trips Guide

**Trip:** {{dates}} | {{travelers description}} | {{budget description}}

---

## OVERVIEW - Quick Comparison
| # | Destination | Type | Cost for {travelers} | Transport | Time needed |
|---|------------|------|-----------|-----------|-------------|
(5-8 day trip options, sorted by distance/cost)

### Recommended Picks
- **Pick 1** - Why
- **Pick 2** - Why
- **Pick 3** - Why

---

# Day Trip: {{Name}} from {{Base City}}

> **Best for:** ...
> **Duration:** ...
> **Distance:** ...

## Getting There
(Transport options with schedules, prices, tips)
> Location: {{lat}}, {{lng}} | {{station/stop address}}

<!-- @vacationeer
id: {{kebab-case-id}}-day-trip
name: {{Name}}
type: day_trip
destination: {{Name}}
total_price_eur: {{number or null}}
total_duration_minutes: {{number}}
location: {{lat}}, {{lng}} | {{main location address}}
expected_score: {{N}}
tips: {{one-line tip or null}}
-->

## What to See
### {{Sub-attraction 1}}
Description...
| | |
|---|---|
| **Price** | ... |
| **Hours** | ... |
> Location: {{lat}}, {{lng}} | {{address}}
> Score: 7/10

<!-- @vacationeer
id: {{kebab-case-id}}
name: {{Sub-attraction 1}}
type: attraction
price_eur: {{number or null}}
duration_minutes: {{number}}
location: {{lat}}, {{lng}} | {{address}}
expected_score: {{N}}
tips: {{one-line tip or null}}
url: {{url or null}}
-->

### {{Sub-attraction 2}}
...

## Suggested Walking Route
(Timed route with waypoints)

## Where to Eat
(2-3 restaurant recommendations with prices)

(Repeat for each day trip)
```

Requirements:
- Include 5-8 day trip options reachable within ~2 hours
- Each sub-attraction MUST have GPS coordinates
- Include transport details (lines, schedules, prices)
- Include restaurant recommendations
- Note any day/time restrictions (e.g. closed Mondays)
- Every day trip heading MUST have a `<!-- @vacationeer ... -->` block with `type: day_trip` (see template). \
Every sub-attraction MUST also have its own `<!-- @vacationeer ... -->` block with `type: attraction`. \
Use kebab-case IDs (e.g. "sagunto-day-trip", "sagunto-roman-theatre").
"""

NO_DAY_TRIPS_SECTION = """\
Skip this file or include only a brief note:
```
# {{Destination}} - Day Trips Guide

Day trips were not requested for this trip. Focus on exploring {{destination}} itself.
```
"""

# --- Conversion templates ---

CONVERSION_SYSTEM = """\
You are a precise data extraction assistant. You convert travel research \
markdown files into structured JSON matching an exact schema. \
Output ONLY valid JSON with no additional text, markdown fences, or explanation."""

CONVERSION_PROMPT = """\
# Task: Convert Travel Research to JSON

Convert the following markdown research files into a single JSON object \
matching the schema below.

## Trip Configuration (use these values for top-level fields)

```json
{config_json}
```

## Target JSON Schema

```json
{schema_json}
```

## Extraction Rules

1. Use the trip config values for: id, name, destination, start_date, end_date, travelers, budget_eur, preferences
2. For `start_date` and `end_date`: {date_instruction}
3. Extract every distinct attraction from the attractions file into the `attractions` array
4. Extract every day trip from the day trips file into the `day_trips` array with `sub_attractions`
5. Generate short kebab-case IDs from names (e.g. "oceanografic", "sagunto-castle")
6. Map to categories: landmark, museum, nature, food, entertainment, transport, accommodation, shopping, day_trip
7. Extract GPS coordinates from `> Location: lat, lng | address` lines or `<!-- @vacationeer -->` blocks
8. Extract expected_score from `> Score: N/10` lines or `<!-- @vacationeer -->` blocks
8b. If `<!-- @vacationeer -->` blocks are present, prefer their values (id, price_eur, duration_minutes, \
location, expected_score, tips, url) as they are machine-formatted
9. Set `user_score` to `null` for all entries
10. Leave `days` as an empty array
11. For day trips, extract outbound/return transport into TravelSegment objects
12. Output ONLY the JSON object — no markdown fences, no explanation

## Source Files

### attractions-and-activities.md
```
{attractions_md}
```

### day-trips.md
```
{day_trips_md}
```

### good-to-know.md
```
{good_to_know_md}
```

Output the complete JSON object now:
"""
