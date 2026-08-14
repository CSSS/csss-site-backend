import csv
import io
import logging
import zipfile
from collections.abc import Iterator
from datetime import date, datetime, timedelta
from typing import Any, cast

import httpx
import sqlalchemy
import sqlalchemy.exc
from google.protobuf.message import DecodeError
from google.transit import gtfs_realtime_pb2
from httpx import AsyncClient

from config import settings
from constants import TZ_INFO
from database import DBSession
from translink.models import BusStatus, TransLinkRealtimeResponse, TransLinkScheduleResponse
from translink.tables import TransLinkRealtimeCacheDB, TransLinkStaticScheduleDB
from translink.types import FeedMessage

REALTIME_URL = "https://gtfsapi.translink.ca/v3/gtfsrealtime"
POSITION_URL = "https://gtfsapi.translink.ca/v3/gtfsposition"
STATIC_URL = "https://gtfs-static.translink.ca/gtfs/google_transit.zip"
REALTIME_CACHE_ID = 1
REALTIME_CACHE_TTL_SECONDS = 90
REALTIME_CACHE_LOCK_ID = 2026062601
STATIC_CACHE_ID = 1
STATIC_CACHE_VERSION = 1
STATIC_CACHE_UNAVAILABLE_MESSAGE = "static TransLink schedule cache is unavailable"

WEEKDAYS = ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday")

type StaticScheduleEntry = dict[str, str | int]
type StaticScheduleCache = dict[str, Any]


class StaticScheduleCacheUnavailableError(RuntimeError):
    """Raised when the preprocessed static schedule cannot serve a date."""


# Taken from the static data.
# Key: Route ID
# 0: Direction ID (always starts from SFU)
# 1: SFU Stop ID
# 2: Route number
BUS_DATA = {
    "6656": (0, "2836", "143"),  # Burquitlam
    "6657": (1, "12972", "144"),  # Metrotown
    "6658": (1, "1875", "145"),  # Production
    "37807": (1, "3129", "R5"),  # Hastings
}


def _gtfs_time_to_seconds(time_str: str) -> int:
    """
    Stop times are in HH:MM:SS format as a 24-hour clock, but they sometimes display times beyond 24:00:00,
    so everything is converted to be an offset of midnight of the day the ride was scheduled.
    """
    h, m, s = map(int, time_str.split(":"))
    return h * 3600 + m * 60 + s


def _iter_gtfs_rows(
    archive: zipfile.ZipFile,
    filename: str,
    required_columns: tuple[str, ...],
) -> Iterator[dict[str, str]]:
    with io.TextIOWrapper(archive.open(filename), encoding="utf-8-sig", newline="") as csv_file:
        reader = csv.DictReader(csv_file)
        if reader.fieldnames is None or not set(required_columns).issubset(reader.fieldnames):
            raise ValueError(f"{filename} is missing required columns")
        for row in reader:
            yield {column: cast(str, row[column]) for column in required_columns}


def parse_static_schedule(content: bytes) -> StaticScheduleCache:
    """Reduce a GTFS archive to the service rules and departures used by the kiosk."""
    try:
        with zipfile.ZipFile(io.BytesIO(content)) as archive:
            filenames = set(archive.namelist())
            if "calendar.txt" not in filenames and "calendar_dates.txt" not in filenames:
                raise ValueError("GTFS archive contains neither calendar.txt nor calendar_dates.txt")

            calendar_rows = (
                list(
                    _iter_gtfs_rows(
                        archive,
                        "calendar.txt",
                        ("service_id", "start_date", "end_date", *WEEKDAYS),
                    )
                )
                if "calendar.txt" in filenames
                else []
            )
            exception_rows = (
                list(
                    _iter_gtfs_rows(
                        archive,
                        "calendar_dates.txt",
                        ("service_id", "date", "exception_type"),
                    )
                )
                if "calendar_dates.txt" in filenames
                else []
            )

            filtered_trips: dict[str, tuple[str, str]] = {}
            for row in _iter_gtfs_rows(
                archive,
                "trips.txt",
                ("trip_id", "route_id", "service_id", "direction_id"),
            ):
                bus_data = BUS_DATA.get(row["route_id"])
                if bus_data is not None and row["direction_id"] == str(bus_data[0]):
                    filtered_trips[row["trip_id"]] = (row["route_id"], row["service_id"])
            if not filtered_trips:
                raise ValueError("GTFS archive contains no trips for the configured routes and directions")

            departures: dict[str, list[StaticScheduleEntry]] = {}
            for row in _iter_gtfs_rows(
                archive,
                "stop_times.txt",
                ("trip_id", "stop_id", "departure_time"),
            ):
                trip = filtered_trips.get(row["trip_id"])
                if trip is None:
                    continue
                route_id, service_id = trip
                _, stop_id, bus_number = BUS_DATA[route_id]
                if row["stop_id"] != stop_id:
                    continue
                departures.setdefault(service_id, []).append(
                    {
                        "trip_id": row["trip_id"],
                        "route_id": route_id,
                        "bus_number": bus_number,
                        "departure_time": row["departure_time"],
                        "departure_seconds": _gtfs_time_to_seconds(row["departure_time"]),
                    }
                )
    except (csv.Error, KeyError, UnicodeDecodeError, ValueError, zipfile.BadZipFile) as e:
        raise RuntimeError(f"Failed to parse static schedule: {e}") from e

    if not departures:
        raise RuntimeError("Static schedule contains no departures for the configured routes")

    relevant_service_ids = set(departures)

    services: dict[str, dict[str, Any]] = {}
    relevant_calendar_rows = (row for row in calendar_rows if row["service_id"] in relevant_service_ids)
    for row in relevant_calendar_rows:
        services[row["service_id"]] = {
            "start_date": row["start_date"],
            "end_date": row["end_date"],
            "weekdays": [index for index, weekday in enumerate(WEEKDAYS) if row[weekday] == "1"],
        }

    exception_map: dict[str, dict[str, list[str]]] = {}
    relevant_exception_rows = [row for row in exception_rows if row["service_id"] in relevant_service_ids]
    for row in relevant_exception_rows:
        exception = exception_map.setdefault(row["date"], {"added": [], "removed": []})
        if row["exception_type"] == "1":
            exception["added"].append(row["service_id"])
        elif row["exception_type"] == "2":
            exception["removed"].append(row["service_id"])

    for schedule in departures.values():
        schedule.sort(key=lambda row: (str(row["route_id"]), int(row["departure_seconds"])))

    coverage_dates = [
        *(row["start_date"] for row in calendar_rows if row["service_id"] in relevant_service_ids),
        *(row["end_date"] for row in calendar_rows if row["service_id"] in relevant_service_ids),
        *(row["date"] for row in relevant_exception_rows),
    ]
    if not coverage_dates:
        raise RuntimeError("Static schedule contains no calendar coverage for the configured routes")

    return {
        "version": STATIC_CACHE_VERSION,
        "coverage": {"start_date": min(coverage_dates), "end_date": max(coverage_dates)},
        "services": services,
        "exceptions": exception_map,
        "departures": departures,
    }


async def fetch_static_schedule(client: AsyncClient) -> StaticScheduleCache:
    """Download and preprocess the static TransLink GTFS feed."""
    try:
        response = await client.get(STATIC_URL)
        response.raise_for_status()
    except httpx.HTTPError as e:
        raise RuntimeError(f"Failed to fetch static schedule: {e}") from e

    logging.info("Downloaded TransLink static schedule (%s bytes); preprocessing", len(response.content))
    schedule = parse_static_schedule(response.content)
    logging.info("Finished preprocessing TransLink static schedule")
    return schedule


async def refresh_static_schedule(db_session: DBSession, client: AsyncClient) -> StaticScheduleCache:
    """Fetch and atomically replace the preprocessed static schedule cache."""
    schedule = await fetch_static_schedule(client)
    try:
        await db_session.merge(
            TransLinkStaticScheduleDB(
                id=STATIC_CACHE_ID,
                date_fetched=datetime.now(tz=TZ_INFO).date(),
                schedule=schedule,
            )
        )
        await db_session.commit()
    except sqlalchemy.exc.SQLAlchemyError as e:
        await db_session.rollback()
        raise RuntimeError(f"Failed to store static schedule: {e}") from e
    return schedule


def resolve_static_schedule(cache: StaticScheduleCache, service_date: date) -> list[StaticScheduleEntry]:
    """Resolve a preprocessed weekly cache into departures for one service date."""
    try:
        if cache["version"] != STATIC_CACHE_VERSION:
            raise ValueError(f"unsupported cache version {cache['version']}")

        date_str = service_date.strftime("%Y%m%d")
        coverage = cache["coverage"]
        if not isinstance(coverage, dict) or not all(
            isinstance(coverage.get(key), str) and len(coverage[key]) == 8 for key in ("start_date", "end_date")
        ):
            raise ValueError("invalid cache coverage")
        if not coverage["start_date"] <= date_str <= coverage["end_date"]:
            raise ValueError(f"date {date_str} is outside cache coverage")

        services = cache["services"]
        departures = cache["departures"]
        if not isinstance(services, dict) or not isinstance(departures, dict):
            raise ValueError("invalid cache services or departures")
        active_services = {
            service_id
            for service_id, service in services.items()
            if service["start_date"] <= date_str <= service["end_date"]
            and service_date.weekday() in service["weekdays"]
        }
        exceptions = cache["exceptions"].get(date_str, {"added": [], "removed": []})
        if not isinstance(exceptions["added"], list) or not isinstance(exceptions["removed"], list):
            raise ValueError("invalid cache exceptions")
        active_services.update(exceptions["added"])
        active_services.difference_update(exceptions["removed"])

        schedule = [row for service_id in active_services for row in departures.get(service_id, [])]
        required_string_fields = ("trip_id", "route_id", "bus_number", "departure_time")
        if any(
            not isinstance(row, dict)
            or any(not isinstance(row.get(field), str) for field in required_string_fields)
            or not isinstance(row.get("departure_seconds"), int)
            for row in schedule
        ):
            raise ValueError("invalid cached departure")
        return sorted(schedule, key=lambda row: (str(row["route_id"]), int(row["departure_seconds"])))
    except (AttributeError, KeyError, TypeError, ValueError) as e:
        raise StaticScheduleCacheUnavailableError(STATIC_CACHE_UNAVAILABLE_MESSAGE) from e


async def get_static_schedule(
    db_session: DBSession, service_date: date | None = None
) -> tuple[date, list[StaticScheduleEntry]]:
    """Read the weekly cache and resolve it for a date without network or bulk parsing work."""
    target_date = service_date or datetime.now(tz=TZ_INFO).date()
    try:
        cached = await db_session.scalar(
            sqlalchemy.select(TransLinkStaticScheduleDB).where(TransLinkStaticScheduleDB.id == STATIC_CACHE_ID)
        )
    except sqlalchemy.exc.SQLAlchemyError as e:
        logging.error("Failed to query static schedule cache: %s", e)
        raise StaticScheduleCacheUnavailableError(STATIC_CACHE_UNAVAILABLE_MESSAGE) from e

    if cached is None:
        raise StaticScheduleCacheUnavailableError(STATIC_CACHE_UNAVAILABLE_MESSAGE)
    return target_date, resolve_static_schedule(cached.schedule, target_date)


def get_next_departures(schedule: list[StaticScheduleEntry], n: int = 3) -> list[StaticScheduleEntry]:
    """
    Get the next few departures for today.

    Args:
        schedule: static schedule filtered for the relevant routes
        n: the number of departures to get for each route

    Returns:
        The next n departures for each route, sorted by route ID and departure time (in seconds).
    """
    now = datetime.now(tz=TZ_INFO)
    current_seconds = int((now - now.replace(hour=0, minute=0, second=0, microsecond=0)).total_seconds())
    upcoming = sorted(
        (row for row in schedule if int(row["departure_seconds"]) > current_seconds),
        key=lambda row: int(row["departure_seconds"]),
    )
    route_counts: dict[str, int] = {}
    result: list[StaticScheduleEntry] = []
    for row in upcoming:
        route_id = str(row["route_id"])
        if route_counts.get(route_id, 0) >= n:
            continue
        result.append(row)
        route_counts[route_id] = route_counts.get(route_id, 0) + 1
    return sorted(result, key=lambda row: (str(row["route_id"]), int(row["departure_seconds"])))


def _parse_feed(content: bytes) -> FeedMessage:
    feed = cast(FeedMessage, gtfs_realtime_pb2.FeedMessage())  # pyright: ignore[reportAttributeAccessIssue]
    feed.ParseFromString(content)
    return feed


def _parse_cached_feed(cached_feed: TransLinkRealtimeCacheDB) -> FeedMessage | None:
    try:
        return _parse_feed(cached_feed.response_bytes)
    except DecodeError as e:
        logging.error(f"Failed to parse cached TransLink realtime feed: {e}")
        return None


def _scheduled_timestamp(departure_seconds: int) -> int:
    now = datetime.now(tz=TZ_INFO)
    midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)
    return int((midnight + timedelta(seconds=departure_seconds)).timestamp())


def _is_realtime_cache_fresh(cached_feed: TransLinkRealtimeCacheDB) -> bool:
    fetched_at = cached_feed.fetched_at
    if fetched_at.tzinfo is None:
        fetched_at = fetched_at.replace(tzinfo=TZ_INFO)

    return datetime.now(tz=TZ_INFO) - fetched_at < timedelta(seconds=REALTIME_CACHE_TTL_SECONDS)


async def fetch_feed(client: AsyncClient, url: str, params: dict[str, Any]) -> FeedMessage | None:
    try:
        response = await client.get(url, params=params)
        response.raise_for_status()
        return _parse_feed(response.content)
    except (httpx.HTTPError, DecodeError) as e:
        logging.error(f"Failed to fetch feed from {url}: {e}")
        return None


async def get_or_fetch_realtime_feed(db_session: DBSession, client: AsyncClient) -> FeedMessage | None:
    cached_feed: TransLinkRealtimeCacheDB | None = None

    try:
        cached_feed = await db_session.scalar(
            sqlalchemy.select(TransLinkRealtimeCacheDB).where(TransLinkRealtimeCacheDB.id == REALTIME_CACHE_ID)
        )
        if cached_feed is not None and _is_realtime_cache_fresh(cached_feed):
            return _parse_cached_feed(cached_feed)

        # Transaction lock, released on commit or rollback.
        # This prevents multiple requests from fetching the feed at the same time.
        await db_session.execute(
            sqlalchemy.text("SELECT pg_advisory_xact_lock(:lock_id)"), {"lock_id": REALTIME_CACHE_LOCK_ID}
        )
        cached_feed = await db_session.scalar(
            sqlalchemy.select(TransLinkRealtimeCacheDB).where(TransLinkRealtimeCacheDB.id == REALTIME_CACHE_ID)
        )

        if cached_feed is not None and _is_realtime_cache_fresh(cached_feed):
            await db_session.commit()
            return _parse_cached_feed(cached_feed)

        response = await client.get(REALTIME_URL, params={"apikey": settings.translink_api_key})
        response.raise_for_status()
        feed = _parse_feed(response.content)
        await db_session.merge(
            TransLinkRealtimeCacheDB(
                id=REALTIME_CACHE_ID,
                fetched_at=datetime.now(tz=TZ_INFO),
                response_bytes=response.content,
            )
        )
        await db_session.commit()
        return feed
    except (httpx.HTTPError, DecodeError) as e:
        logging.error(f"Failed to fetch realtime feed from {REALTIME_URL}: {e}")
        await db_session.rollback()
        if cached_feed is not None:
            return _parse_cached_feed(cached_feed)
        return None
    except sqlalchemy.exc.SQLAlchemyError as e:
        logging.error(f"Failed to use TransLink realtime cache: {e}")
        await db_session.rollback()
        return None


async def fetch_realtime_schedule(db_session: DBSession, client: AsyncClient) -> list[TransLinkRealtimeResponse]:
    # FeedMessage is generated at runtime, so the type checker can't find this function
    trip_feed = await get_or_fetch_realtime_feed(db_session, client)

    if trip_feed is None:
        return []

    result: list[TransLinkRealtimeResponse] = []
    for entity in trip_feed.entity:
        if not entity.HasField("trip_update"):
            continue

        tu = entity.trip_update
        trip = tu.trip
        bus_data = BUS_DATA.get(trip.route_id)

        if bus_data is None or trip.direction_id != bus_data[0]:
            continue

        _, stop_id, bus_number = bus_data
        stop = next((s for s in tu.stop_time_update if s.stop_id == stop_id), None)
        if stop is None:
            continue

        result.append(
            TransLinkRealtimeResponse(
                route_number=bus_number,
                scheduled_departure_time=stop.departure.time - stop.departure.delay,
                realtime_time=stop.departure.time,
                delay_seconds=stop.departure.delay,
            )
        )

    result.sort(key=lambda e: e.realtime_time)
    return result


async def get_departure_statuses(db_session: DBSession, client: AsyncClient) -> list[TransLinkScheduleResponse]:
    """
    Gets the real-time bus schedule from the TransLink GTFS Realtime API and merge it with the static data.
    """

    def _response_from_static_row(row: Any, delay: int = 0, status: BusStatus = BusStatus.OnTime):
        scheduled_time = _scheduled_timestamp(cast(int, row["departure_seconds"]))
        return TransLinkScheduleResponse(
            route_number=cast(str, row["bus_number"]),
            scheduled_departure_time=scheduled_time,
            realtime_time=scheduled_time + delay,
            delay_seconds=delay,
            status=status,
        )

    _, schedule = await get_static_schedule(db_session)
    next_departures = get_next_departures(schedule)
    trip_feed = await get_or_fetch_realtime_feed(db_session, client)
    # If the trip feed fails to fetch then just return information from the static schedule.
    if trip_feed is None:
        return [_response_from_static_row(row) for row in next_departures]
    # FeedMessage is generated at runtime, so the type checker can't find this function

    # Map all the realtime data to each bus's status
    realtime_map: dict[str, tuple[int, BusStatus]] = {}
    for entity in trip_feed.entity:
        if not entity.HasField("trip_update"):
            continue

        trip_update = entity.trip_update
        trip = trip_update.trip
        bus_data = BUS_DATA.get(trip.route_id)
        if bus_data is None or trip.direction_id != bus_data[0]:
            continue

        if trip.schedule_relationship == gtfs_realtime_pb2.TripDescriptor.CANCELED:  # pyright: ignore[reportAttributeAccessIssue]
            realtime_map[trip.trip_id] = (0, BusStatus.Cancelled)
            continue

        _, stop_id, _ = bus_data
        stop = next((s for s in trip_update.stop_time_update if s.stop_id == stop_id), None)
        if stop is None:
            continue

        first_stop = min(trip_update.stop_time_update, key=lambda s: s.stop_sequence)
        if first_stop.stop_id == stop_id:
            status = BusStatus.Arrived
        elif stop.departure.delay > 0:
            status = BusStatus.Delayed
        else:
            status = BusStatus.OnTime

        realtime_map[trip.trip_id] = (stop.departure.delay, status)

    return [
        _response_from_static_row(
            row,
            *realtime_map.get(cast(str, row["trip_id"]), (0, BusStatus.OnTime)),
        )
        for row in next_departures
    ]
