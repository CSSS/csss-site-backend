# ruff: noqa: N802
from collections.abc import Iterator
from typing import Protocol

from translink.models import BusStatus


class Trip(Protocol):
    trip_id: str
    route_id: str
    direction_id: int


class StopTimeUpdate(Protocol):
    stop_sequence: int
    stop_id: str

    class _Time(Protocol):
        time: int
        delay: int

    arrival: _Time
    departure: _Time


class TripUpdate(Protocol):
    class _Vehicle(Protocol):
        id: str

    trip: Trip
    vehicle: _Vehicle
    stop_time_update: list[StopTimeUpdate]

    def HasField(self, name: str) -> bool: ...


class FeedEntity(Protocol):
    class _Vehicle(Protocol):
        trip: Trip
        current_status: BusStatus

    trip_update: TripUpdate
    vehicle: _Vehicle

    def HasField(self, name: str) -> bool: ...


class FeedMessage(Protocol):
    entity: Iterator[FeedEntity]

    def ParseFromString(self, data: bytes) -> int: ...
