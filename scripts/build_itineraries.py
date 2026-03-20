"""Build 3 itineraries for the Valencia 2026 trip and save to trip.json."""
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from vacationeer.models.trip import Activity, Category, Day, Itinerary, _id
from vacationeer.storage.json_store import JsonTripStore

store = JsonTripStore(Path("trips/valencia-2026/trip.json"))
trip = store.load()


def make_day(d, label, attraction_ids, day_trip_id=None, notes=None):
    day = Day(date=d, label=label, notes=notes)

    if day_trip_id:
        dt = next(dt for dt in trip.day_trips if dt.id == day_trip_id)
        if dt.outbound:
            seg = dt.outbound
            day.activities.append(Activity(
                day_trip_id=dt.id,
                name=f"Travel to {dt.destination} ({seg.mode.value})",
                duration_minutes=seg.duration_minutes,
                price_eur=seg.price_eur,
                category=Category.TRANSPORT,
            ))
        for sub in dt.sub_attractions:
            day.activities.append(Activity(
                attraction_id=sub.id,
                day_trip_id=dt.id,
                name=sub.name,
                duration_minutes=sub.duration_minutes,
                price_eur=sub.price_eur,
                category=sub.category,
            ))
        if dt.return_trip:
            seg = dt.return_trip
            day.activities.append(Activity(
                day_trip_id=dt.id,
                name=f"Return from {dt.destination} ({seg.mode.value})",
                duration_minutes=seg.duration_minutes,
                price_eur=seg.price_eur,
                category=Category.TRANSPORT,
            ))

    for aid in attraction_ids:
        a = next((a for a in trip.attractions if a.id == aid), None)
        if a:
            day.activities.append(Activity(
                attraction_id=a.id,
                name=a.name,
                duration_minutes=a.duration_minutes,
                price_eur=a.price_eur,
                category=a.category,
            ))
    return day


# ================================================================
# ITINERARY A - Balanced Explorer (Recommended)
# ================================================================
itin_a = Itinerary(
    id="itin-a",
    name="A \u2014 Balanced Explorer",
    description="Best of everything. One day trip, all major sights, good pacing. ~360-400 EUR/pp.",
)
itin_a.days = [
    make_day(date(2026, 3, 21), "Arrival + First Impressions",
        ["plaza-del-ayuntamiento", "horchateria-santa-catalina", "portal-valldigna",
         "plaza-tossal-art", "atenea-sky", "tasca-angel"],
        notes="Light day. Walk old town, street art, rooftop sunset, tapas dinner."),

    make_day(date(2026, 3, 22), "Free Museum Sunday",
        ["la-lonja", "mercado-central", "torres-serranos", "torres-de-quart",
         "almoina", "dos-aguas-courtyard", "pichiavo-ruzafa", "heladeria-veneta"],
        notes="Stack all free entries. Walking tour in morning (book Civitatis/GuruWalk). IVAM free today too."),

    make_day(date(2026, 3, 23), "Bioparc + Turia Cycling + Beach",
        ["bioparc", "gulliver-park", "city-of-arts-exterior", "playa-malvarrosa", "casa-montana"],
        notes="Monday = museums closed. Zoo morning, cycle Turia Gardens, beach afternoon. Activate 72h Tourist Card."),

    make_day(date(2026, 3, 24), "Oceanografic + City of Arts & Sciences",
        ["oceanografic", "science-museum", "hemisferic", "museo-fallero", "masusa-paella"],
        notes="Full day at the complex. Dolphin show ~11:45. Start at Arctic end. Lunch inside. Paella dinner in Ruzafa."),

    make_day(date(2026, 3, 25), "Albufera Day Trip", [],
        day_trip_id="albufera-day-trip",
        notes="Nature day. Birdwatching at Raco de l'Olla, La Devesa trails, paella lunch in El Palmar, sunset boat ride."),

    make_day(date(2026, 3, 26), "Day Trip: Sagunto",
        ["cathedral"],
        day_trip_id="sagunto-day-trip",
        notes="Morning: castle + Roman theatre + Jewish quarter (all free). Back by 15:00. Evening: Cathedral + bell tower."),

    make_day(date(2026, 3, 27), "Hidden Gems + Chill Day",
        ["jardin-monforte", "museo-bellas-artes", "viveros-gardens", "cabanyal-progres",
         "tallat-coffee", "jardin-botanico", "jardin-hesperides", "veles-e-vents"],
        notes="Slower pace. Secret gardens, Cabanyal tiles, botanical garden, Marina sunset."),

    make_day(date(2026, 3, 28), "Departure",
        ["bluebell-coffee", "mercado-central"],
        notes="Last coffee at Bluebell. Souvenirs at Mercado Central. Metro to airport."),
]

# ================================================================
# ITINERARY B - Two Day Trips + Active
# ================================================================
itin_b = Itinerary(
    id="itin-b",
    name="B \u2014 Two Day Trips",
    description="More ambitious. Sagunto morning + Albufera evening on Wed, full Xativa Thu. ~380-430 EUR/pp.",
)
itin_b.days = [
    make_day(date(2026, 3, 21), "Arrival + First Impressions",
        ["plaza-del-ayuntamiento", "horchateria-santa-catalina", "portal-valldigna",
         "plaza-tossal-art", "atenea-sky", "tasca-angel"],
        notes="Same as A."),

    make_day(date(2026, 3, 22), "Free Museum Sunday",
        ["la-lonja", "mercado-central", "torres-serranos", "torres-de-quart",
         "almoina", "dos-aguas-courtyard", "pichiavo-ruzafa", "heladeria-veneta"],
        notes="Stack all free entries. Walking tour morning."),

    make_day(date(2026, 3, 23), "Bioparc + Turia Cycling + Beach",
        ["bioparc", "gulliver-park", "city-of-arts-exterior", "playa-malvarrosa", "casa-montana"],
        notes="Monday = museums closed. Zoo + cycling + beach. Activate Tourist Card."),

    make_day(date(2026, 3, 24), "Oceanografic + City of Arts & Sciences",
        ["oceanografic", "science-museum", "hemisferic", "museo-fallero", "masusa-paella"],
        notes="Full day at the complex."),

    make_day(date(2026, 3, 25), "Sagunto Morning + Albufera Sunset",
        [],
        day_trip_id="sagunto-day-trip",
        notes="Early train to Sagunto (castle + theatre, back by 14:00). Bus #24 to El Palmar for paella + sunset boat. Long day!"),

    make_day(date(2026, 3, 26), "Day Trip: Xativa", [],
        day_trip_id="xativa-day-trip",
        notes="Full day. Double castle, Borgia history, upside-down king. Train ~50 min. Book castle tickets online!"),

    make_day(date(2026, 3, 27), "Hidden Gems + Cabanyal + Chill",
        ["jardin-monforte", "museo-bellas-artes", "cabanyal-progres", "jardin-botanico",
         "ubik-cafe", "terraza-270"],
        notes="Slower pace. Gardens, Cabanyal tiles, Ruzafa, City of Arts sunset from Terraza 270."),

    make_day(date(2026, 3, 28), "Departure",
        ["bluebell-coffee", "mercado-central"],
        notes="Last coffee. Souvenirs. Metro to airport."),
]

# ================================================================
# ITINERARY C - Relaxed & Romantic
# ================================================================
itin_c = Itinerary(
    id="itin-c",
    name="C \u2014 Relaxed & Romantic",
    description="Slower pace, food focus, no day trips outside Valencia. More time at each place. ~320-370 EUR/pp.",
)
itin_c.days = [
    make_day(date(2026, 3, 21), "Arrival + Old Town Evening",
        ["plaza-del-ayuntamiento", "horchateria-santa-catalina", "atenea-sky", "bodega-rentaora"],
        notes="Light arrival day. Old town walk, horchata, rooftop sunset, old-school tapas."),

    make_day(date(2026, 3, 22), "Free Museum Sunday (Relaxed)",
        ["la-lonja", "mercado-central", "torres-serranos", "almoina",
         "dos-aguas-courtyard", "heladeria-veneta", "olhops"],
        notes="Fewer museums, longer lunch. Walking tour morning. Craft beer in Ruzafa evening."),

    make_day(date(2026, 3, 23), "Albufera by Bike", [],
        day_trip_id="albufera-day-trip",
        notes="Cycle 20 km to El Palmar through rice fields. Paella lunch. Boat ride. Cycle back or bus. Monday = no museum conflict."),

    make_day(date(2026, 3, 24), "Bioparc + Cathedral + Turia",
        ["bioparc", "turia-gardens", "puente-flores", "cathedral"],
        notes="Zoo morning (animals most active). Cycle Turia afternoon. Cathedral + bell tower before closing."),

    make_day(date(2026, 3, 25), "Oceanografic (Full Day, No Rush)",
        ["oceanografic", "pont-assut-or", "terraza-270"],
        notes="Take your time. All zones + dolphin show + leisurely lunch inside. Sunset drinks at Terraza 270."),

    make_day(date(2026, 3, 26), "Science + Cabanyal + Beach",
        ["science-museum", "hemisferic", "cabanyal-progres", "casa-gargoles",
         "playa-patacona", "casa-montana"],
        notes="Science Museum morning. Cabanyal tile walk afternoon. Beach stroll to Patacona. Casa Montana dinner."),

    make_day(date(2026, 3, 27), "Gardens + Ruzafa Food Crawl",
        ["jardin-monforte", "jardin-botanico", "cccc-cloisters", "blackbird-cafe",
         "ubik-cafe", "gnomo-shop", "marina-beach-club"],
        notes="Morning: secret gardens. Afternoon: Ruzafa neighbourhood crawl. Evening: Marina Beach Club sunset."),

    make_day(date(2026, 3, 28), "Departure",
        ["casa-fran", "mercado-central"],
        notes="Coffee at Casa Fran. Souvenirs at Mercado Central."),
]

# ================================================================
# Save
# ================================================================
trip.itineraries = [itin_a, itin_b, itin_c]
trip.active_itinerary_id = "itin-a"

store.save(trip)

for i in trip.itineraries:
    total_acts = sum(len(d.activities) for d in i.days)
    print(f"{i.name}: {len(i.days)} days, {total_acts} activities")
    for d in i.days:
        print(f"  {d.date} {d.label}: {len(d.activities)} acts")

print(f"\nActive: {trip.active_itinerary_id}")
print("Saved!")
