from __future__ import annotations

from datetime import date, time, timedelta
from typing import Optional

from vacationeer.models.trip import (
    Activity,
    Attraction,
    Category,
    Day,
    DayTrip,
    Trip,
    _id,
)


def init_days(trip: Trip) -> Trip:
    """Create an empty Day for each date in [start_date, end_date].

    Skips dates that already have a Day.
    """
    existing_dates = {day.date for day in trip.days}
    current = trip.start_date
    while current <= trip.end_date:
        if current not in existing_dates:
            trip.days.append(Day(date=current))
        current += timedelta(days=1)
    trip.days.sort(key=lambda d: d.date)
    return trip


def _find_day(trip: Trip, target_date: date) -> Day:
    for day in trip.days:
        if day.date == target_date:
            return day
    raise ValueError(f"No day found for {target_date}. Run init-days first.")


def _find_attraction(trip: Trip, attraction_id: str) -> Attraction:
    for a in trip.attractions:
        if a.id == attraction_id:
            return a
    raise ValueError(f"Attraction {attraction_id!r} not found.")


def _find_day_trip(trip: Trip, day_trip_id: str) -> DayTrip:
    for dt in trip.day_trips:
        if dt.id == day_trip_id:
            return dt
    raise ValueError(f"DayTrip {day_trip_id!r} not found.")


def schedule(
    trip: Trip,
    attraction_id: str,
    target_date: date,
    start_time: Optional[time] = None,
) -> Trip:
    """Create an Activity from an Attraction and add it to the specified Day."""
    attraction = _find_attraction(trip, attraction_id)
    day = _find_day(trip, target_date)

    activity = Activity(
        attraction_id=attraction.id,
        name=attraction.name,
        start_time=start_time,
        duration_minutes=attraction.duration_minutes,
        price_eur=attraction.price_eur,
        category=attraction.category,
    )
    day.activities.append(activity)
    return trip


def schedule_day_trip(
    trip: Trip,
    day_trip_id: str,
    target_date: date,
    departure_time: Optional[time] = None,
) -> Trip:
    """Expand a DayTrip into Activities on a Day.

    Creates: outbound travel + sub-attraction activities + return travel.
    Sets the day label to the day trip name.
    """
    day_trip = _find_day_trip(trip, day_trip_id)
    day = _find_day(trip, target_date)

    day.label = day_trip.name

    # Outbound travel
    if day_trip.outbound:
        seg = day_trip.outbound
        day.activities.append(Activity(
            day_trip_id=day_trip.id,
            name=f"Travel to {day_trip.destination} ({seg.mode.value})",
            start_time=departure_time or seg.departure_time,
            duration_minutes=seg.duration_minutes,
            price_eur=seg.price_eur,
            category=Category.TRANSPORT,
            notes=seg.notes,
        ))

    # Sub-attractions
    for attr in day_trip.sub_attractions:
        day.activities.append(Activity(
            attraction_id=attr.id,
            day_trip_id=day_trip.id,
            name=attr.name,
            duration_minutes=attr.duration_minutes,
            price_eur=attr.price_eur,
            category=attr.category,
        ))

    # Return travel
    if day_trip.return_trip:
        seg = day_trip.return_trip
        day.activities.append(Activity(
            day_trip_id=day_trip.id,
            name=f"Return from {day_trip.destination} ({seg.mode.value})",
            start_time=seg.departure_time,
            duration_minutes=seg.duration_minutes,
            price_eur=seg.price_eur,
            category=Category.TRANSPORT,
            notes=seg.notes,
        ))

    return trip


def unschedule(trip: Trip, activity_id: str) -> Trip:
    """Remove an Activity from its Day by activity ID."""
    for day in trip.days:
        day.activities = [a for a in day.activities if a.id != activity_id]
    return trip


def get_unscheduled(trip: Trip) -> tuple[list[Attraction], list[DayTrip]]:
    """Return attractions and day trips not assigned to any day."""
    scheduled_attraction_ids = {
        act.attraction_id
        for day in trip.days
        for act in day.activities
        if act.attraction_id
    }
    scheduled_day_trip_ids = {
        act.day_trip_id
        for day in trip.days
        for act in day.activities
        if act.day_trip_id
    }

    unscheduled_attractions = [
        a for a in trip.attractions if a.id not in scheduled_attraction_ids
    ]
    unscheduled_day_trips = [
        dt for dt in trip.day_trips if dt.id not in scheduled_day_trip_ids
    ]
    return unscheduled_attractions, unscheduled_day_trips


def swap_days(trip: Trip, date1: date, date2: date) -> Trip:
    """Swap all activities and labels between two days."""
    day1 = _find_day(trip, date1)
    day2 = _find_day(trip, date2)

    day1.activities, day2.activities = day2.activities, day1.activities
    day1.label, day2.label = day2.label, day1.label
    day1.notes, day2.notes = day2.notes, day1.notes
    day1.start_time, day2.start_time = day2.start_time, day1.start_time
    return trip


def move_activity(trip: Trip, activity_id: str, target_date: date) -> Trip:
    """Move an activity from its current day to another day."""
    target_day = _find_day(trip, target_date)
    activity = None

    for day in trip.days:
        for act in day.activities:
            if act.id == activity_id:
                activity = act
                day.activities.remove(act)
                break
        if activity:
            break

    if activity is None:
        raise ValueError(f"Activity {activity_id!r} not found in any day.")

    target_day.activities.append(activity)
    return trip
