from __future__ import annotations

from datetime import date, time
from enum import Enum
from typing import Optional
from uuid import uuid4

from pydantic import BaseModel, Field, model_validator


def _id() -> str:
    return uuid4().hex[:8]


class Category(str, Enum):
    LANDMARK = "landmark"
    MUSEUM = "museum"
    NATURE = "nature"
    FOOD = "food"
    ENTERTAINMENT = "entertainment"
    TRANSPORT = "transport"
    ACCOMMODATION = "accommodation"
    SHOPPING = "shopping"
    DAY_TRIP = "day_trip"
    INFRASTRUCTURE = "infrastructure"


class TravelMode(str, Enum):
    TRAIN = "train"
    BUS = "bus"
    CAR = "car"
    WALK = "walk"
    BOAT = "boat"
    METRO = "metro"


class Location(BaseModel):
    lat: float
    lng: float
    address: Optional[str] = None


class Attraction(BaseModel):
    id: str = Field(default_factory=_id)
    name: str
    description: Optional[str] = None
    location: Location
    category: Category
    price_eur: Optional[float] = None
    duration_minutes: Optional[int] = None
    tags: list[str] = Field(default_factory=list)
    tips: Optional[str] = None
    url: Optional[str] = None
    expected_score: Optional[float] = None
    user_score: Optional[float] = None


class TravelSegment(BaseModel):
    mode: TravelMode
    origin: str
    destination: str
    departure_time: Optional[time] = None
    arrival_time: Optional[time] = None
    duration_minutes: Optional[int] = None
    price_eur: Optional[float] = None
    booking_reference: Optional[str] = None
    notes: Optional[str] = None


class Activity(BaseModel):
    id: str = Field(default_factory=_id)
    attraction_id: Optional[str] = None
    day_trip_id: Optional[str] = None
    name: str
    start_time: Optional[time] = None
    duration_minutes: Optional[int] = None
    price_eur: Optional[float] = None
    category: Optional[Category] = None
    travel_from_prev_minutes: Optional[int] = None
    status: str = "planned"  # planned, confirmed, done, skipped
    notes: Optional[str] = None


class Day(BaseModel):
    date: date
    label: Optional[str] = None
    start_time: Optional[time] = None
    activities: list[Activity] = Field(default_factory=list)
    notes: Optional[str] = None


class DayTrip(BaseModel):
    id: str = Field(default_factory=_id)
    name: str
    destination: str
    description: Optional[str] = None
    location: Location
    sub_attractions: list[Attraction] = Field(default_factory=list)
    outbound: Optional[TravelSegment] = None
    return_trip: Optional[TravelSegment] = None
    total_price_eur: Optional[float] = None
    total_duration_minutes: Optional[int] = None
    tags: list[str] = Field(default_factory=list)
    tips: Optional[str] = None
    expected_score: Optional[float] = None
    user_score: Optional[float] = None


class Grouping(BaseModel):
    id: str = Field(default_factory=_id)
    name: str
    description: Optional[str] = None
    color: str = "#3498db"
    parent_id: Optional[str] = None
    member_ids: list[str] = Field(default_factory=list)


class Itinerary(BaseModel):
    id: str = Field(default_factory=_id)
    name: str = "Itinerary A"
    description: Optional[str] = None
    days: list[Day] = Field(default_factory=list)


class Preferences(BaseModel):
    interests: list[str] = Field(default_factory=list)
    avoid: list[str] = Field(default_factory=list)
    pace: str = "moderate"
    budget_per_day_eur: Optional[float] = None


class Trip(BaseModel):
    id: str = Field(default_factory=_id)
    name: str
    destination: str
    start_date: date
    end_date: date
    travelers: int = 2
    budget_eur: Optional[float] = None
    preferences: Optional[Preferences] = None
    attractions: list[Attraction] = Field(default_factory=list)
    day_trips: list[DayTrip] = Field(default_factory=list)
    groupings: list[Grouping] = Field(default_factory=list)
    days: list[Day] = Field(default_factory=list)
    itineraries: list[Itinerary] = Field(default_factory=list)
    active_itinerary_id: Optional[str] = None

    @model_validator(mode="after")
    def _migrate_days_to_itineraries(self) -> "Trip":
        if self.days and not self.itineraries:
            itin = Itinerary(id="default", name="Itinerary A", days=self.days)
            self.itineraries = [itin]
            self.active_itinerary_id = "default"
            self.days = []
        if not self.active_itinerary_id and self.itineraries:
            self.active_itinerary_id = self.itineraries[0].id
        return self

    @property
    def active_itinerary(self) -> Optional[Itinerary]:
        return next(
            (i for i in self.itineraries if i.id == self.active_itinerary_id),
            self.itineraries[0] if self.itineraries else None,
        )

    @property
    def dest_slug(self) -> str:
        return self.destination.lower().replace(" ", "-")
