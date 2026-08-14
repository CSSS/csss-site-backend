import csv
import io
import zipfile
from datetime import date, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from fastapi import status
from google.transit import gtfs_realtime_pb2
from httpx import AsyncClient, Request, Response

from constants import TZ_INFO
from translink.crud import (
    BUS_DATA,
    STATIC_CACHE_UNAVAILABLE_MESSAGE,
    STATIC_CACHE_VERSION,
    StaticScheduleCacheUnavailableError,
    _gtfs_time_to_seconds,
    fetch_realtime_schedule,
    fetch_static_schedule,
    get_departure_statuses,
    get_next_departures,
    get_or_fetch_realtime_feed,
    get_static_schedule,
    refresh_static_schedule,
    resolve_static_schedule,
)
from translink.models import BusStatus, TransLinkRealtimeResponse, TransLinkScheduleResponse
from translink.tables import TransLinkRealtimeCacheDB, TransLinkStaticScheduleDB

pytestmark = pytest.mark.asyncio(loop_scope="session")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def rows_to_csv(rows: list[dict[str, str]]) -> str:
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=list(rows[0]))
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue()


def make_gtfs_zip(departure_time: str = "23:00:00", active_weekdays: set[int] | None = None) -> bytes:
    """
    Return a minimal but valid GTFS zip whose single service is active today,
    with one trip per route in BUS_DATA.

    `departure_time` is used for all stop_times rows — set it in the future
    (the default "23:00:00" works for most of the day) so get_next_departures
    includes them.
    """
    buf = io.BytesIO()
    all_days = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
    active_weekdays = active_weekdays or {datetime.now(tz=TZ_INFO).weekday()}

    with zipfile.ZipFile(buf, "w") as z:
        cal_row = {day: ("1" if index in active_weekdays else "0") for index, day in enumerate(all_days)}
        cal_row.update({"service_id": "SVC1", "start_date": "20240101", "end_date": "20991231"})
        z.writestr("calendar.txt", rows_to_csv([cal_row]))

        # calendar_dates.txt - no exceptions
        z.writestr("calendar_dates.txt", "date,service_id,exception_type\n")

        # trips.txt - one trip per (route_id, direction_id) pair in BUS_DATA
        trips_rows = [
            {"trip_id": f"trip_{num}", "route_id": rid, "service_id": "SVC1", "direction_id": str(did)}
            for rid, (did, _sid, num) in BUS_DATA.items()
        ]
        z.writestr("trips.txt", rows_to_csv(trips_rows))

        # stop_times.txt - one stop per trip at the correct SFU bus loop stop
        stop_rows = [
            {"trip_id": f"trip_{num}", "stop_id": sid, "departure_time": departure_time}
            for _rid, (_, sid, num) in BUS_DATA.items()
        ]
        z.writestr("stop_times.txt", rows_to_csv(stop_rows))

    return buf.getvalue()


def make_feed_bytes(
    trip_id: str,
    route_id: str,
    direction_id: int,
    stop_id: str,
    departure_unix: int,
    delay: int = 0,
    cancelled: bool = False,
) -> bytes:
    """Return a serialised GTFS-RT FeedMessage with a single trip-update entity."""
    feed = gtfs_realtime_pb2.FeedMessage()  # pyright: ignore[reportAttributeAccessIssue]
    feed.header.gtfs_realtime_version = "2.0"
    feed.header.timestamp = departure_unix

    entity = feed.entity.add()
    entity.id = "e1"
    tu = entity.trip_update
    tu.trip.trip_id = trip_id
    tu.trip.route_id = route_id
    tu.trip.direction_id = direction_id

    if cancelled:
        tu.trip.schedule_relationship = gtfs_realtime_pb2.TripDescriptor.CANCELED  # pyright: ignore[reportAttributeAccessIssue]
    else:
        stu = tu.stop_time_update.add()
        stu.stop_sequence = 1
        stu.stop_id = stop_id
        stu.departure.time = departure_unix
        stu.departure.delay = delay

    return feed.SerializeToString()


def make_empty_feed_bytes() -> bytes:
    feed = gtfs_realtime_pb2.FeedMessage()  # pyright: ignore[reportAttributeAccessIssue]
    feed.header.gtfs_realtime_version = "2.0"
    return feed.SerializeToString()


def mock_http_client(content: bytes) -> AsyncMock:
    """Return an AsyncMock httpx client whose .get() always returns `content`."""
    resp = MagicMock(spec=Response)
    resp.content = content
    client = AsyncMock(spec=AsyncClient)
    client.get = AsyncMock(return_value=resp)
    return client


def mock_db_session(cached_row=None) -> AsyncMock:
    """
    Return an AsyncMock DB session.
    `cached_row` is what scalar() will return — pass None to simulate a cache miss.
    """
    session = AsyncMock()
    session.scalar = AsyncMock(return_value=cached_row)
    session.merge = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    return session


def make_static_cache(
    schedule: list[dict],
    service_date: date | None = None,
    *,
    version: int = STATIC_CACHE_VERSION,
) -> dict:
    target_date = service_date or datetime.now(tz=TZ_INFO).date()
    date_str = target_date.strftime("%Y%m%d")
    return {
        "version": version,
        "coverage": {"start_date": date_str, "end_date": date_str},
        "services": {
            "SVC1": {
                "start_date": date_str,
                "end_date": date_str,
                "weekdays": [target_date.weekday()],
            }
        },
        "exceptions": {},
        "departures": {"SVC1": schedule},
    }


# ---------------------------------------------------------------------------
# Unit tests — pure functions
# ---------------------------------------------------------------------------


async def test__gtfs_time_to_seconds_normal_times():
    assert _gtfs_time_to_seconds("00:00:00") == 0
    assert _gtfs_time_to_seconds("01:00:00") == 3600
    assert _gtfs_time_to_seconds("00:01:00") == 60
    assert _gtfs_time_to_seconds("00:00:01") == 1
    assert _gtfs_time_to_seconds("12:34:56") == 12 * 3600 + 34 * 60 + 56


async def test__gtfs_time_to_seconds_past_midnight():
    # GTFS allows times > 24:00 for trips that started the previous service day
    assert _gtfs_time_to_seconds("25:00:00") == 25 * 3600
    assert _gtfs_time_to_seconds("26:30:45") == 26 * 3600 + 30 * 60 + 45


async def test__get_next_departures_filters_past():
    now = datetime.now(tz=TZ_INFO)
    midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)
    now_secs = int((now - midnight).total_seconds())

    schedule = [
        # Already departed - must be excluded
        {
            "trip_id": "past_trip",
            "route_id": "6656",
            "bus_number": "143",
            "departure_time": "00:01:00",
            "departure_seconds": 60,
        },
        # Future - must be included
        {
            "trip_id": "future_trip",
            "route_id": "6656",
            "bus_number": "143",
            "departure_time": "23:00:00",
            "departure_seconds": now_secs + 3600,
        },
    ]

    result = get_next_departures(schedule, n=3)
    assert len(result) == 1
    assert result[0]["trip_id"] == "future_trip"


async def test__get_next_departures_respects_n():
    now = datetime.now(tz=TZ_INFO)
    midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)
    now_secs = int((now - midnight).total_seconds())

    # Five future trips on the same route - n=2 should limit to 2
    schedule = [
        {
            "trip_id": f"trip_{i}",
            "route_id": "6656",
            "bus_number": "143",
            "departure_time": "23:00:00",
            "departure_seconds": now_secs + i * 600,
        }
        for i in range(1, 6)
    ]

    assert len(get_next_departures(schedule, n=2)) == 2
    assert len(get_next_departures(schedule, n=1)) == 1


async def test__get_next_departures_multiple_routes():
    now = datetime.now(tz=TZ_INFO)
    midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)
    now_secs = int((now - midnight).total_seconds())

    schedule = [
        {
            "trip_id": f"trip_{rid}_{i}",
            "route_id": rid,
            "bus_number": num,
            "departure_time": "23:00:00",
            "departure_seconds": now_secs + i * 600,
        }
        for rid, (_, _, num) in BUS_DATA.items()
        for i in range(1, 4)
    ]

    result = get_next_departures(schedule, n=2)
    assert len(result) == 8
    assert {row["route_id"] for row in result} == set(BUS_DATA)


# ---------------------------------------------------------------------------
# Tests for fetch_static_schedule
# ---------------------------------------------------------------------------


async def test__fetch_static_schedule_returns_all_routes():
    client = mock_http_client(make_gtfs_zip())
    cache = await fetch_static_schedule(client)
    schedule = resolve_static_schedule(cache, datetime.now(tz=TZ_INFO).date())

    assert schedule
    expected_cols = {"trip_id", "route_id", "bus_number", "departure_time", "departure_seconds"}
    assert expected_cols.issubset(schedule[0])
    assert {row["bus_number"] for row in schedule} == {num for _, (_, _, num) in BUS_DATA.items()}


async def test__weekly_cache_resolves_multiple_weekdays_without_refetching():
    client = mock_http_client(make_gtfs_zip(active_weekdays=set(range(7))))
    cache = await fetch_static_schedule(client)
    today = datetime.now(tz=TZ_INFO).date()

    assert len(resolve_static_schedule(cache, today)) == len(BUS_DATA)
    assert len(resolve_static_schedule(cache, today + timedelta(days=1))) == len(BUS_DATA)
    client.get.assert_awaited_once()


async def test__fetch_static_schedule_excludes_wrong_direction():
    """Trips are direction-filtered; a wrong-direction trip should not appear."""
    buf = io.BytesIO()
    all_days = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
    current_weekday = datetime.now(tz=TZ_INFO).weekday()

    with zipfile.ZipFile(buf, "w") as z:
        cal_row = {day: ("1" if index == current_weekday else "0") for index, day in enumerate(all_days)}
        cal_row.update({"service_id": "SVC1", "start_date": "20240101", "end_date": "20991231"})
        z.writestr("calendar.txt", rows_to_csv([cal_row]))
        z.writestr("calendar_dates.txt", "date,service_id,exception_type\n")

        # Route 6656 expects direction_id=0; give it direction_id=1
        z.writestr(
            "trips.txt",
            rows_to_csv([{"trip_id": "wrong_dir", "route_id": "6656", "service_id": "SVC1", "direction_id": "1"}]),
        )
        z.writestr(
            "stop_times.txt",
            rows_to_csv([{"trip_id": "wrong_dir", "stop_id": "2836", "departure_time": "23:00:00"}]),
        )

    client = mock_http_client(buf.getvalue())
    with pytest.raises(RuntimeError, match="no trips"):
        await fetch_static_schedule(client)


async def test__fetch_static_schedule_raises_on_http_error():
    import httpx

    client = AsyncMock(spec=AsyncClient)
    client.get = AsyncMock(side_effect=httpx.HTTPError("connection refused"))

    with pytest.raises(RuntimeError, match="Failed to fetch static schedule"):
        await fetch_static_schedule(client)


async def test__fetch_static_schedule_raises_on_http_error_status():
    client = AsyncMock(spec=AsyncClient)
    client.get = AsyncMock(
        return_value=Response(
            status_code=500,
            request=Request("GET", "https://gtfs-static.translink.ca/gtfs/google_transit.zip"),
        )
    )

    with pytest.raises(RuntimeError, match="Failed to fetch static schedule"):
        await fetch_static_schedule(client)


async def test__fetch_static_schedule_raises_on_bad_zip():
    client = mock_http_client(b"this is not a zip")

    with pytest.raises(RuntimeError, match="Failed to parse static schedule"):
        await fetch_static_schedule(client)


# ---------------------------------------------------------------------------
# Tests for fetch_realtime_schedule
# ---------------------------------------------------------------------------


async def test__fetch_realtime_schedule_parses_single_entity():
    departure_unix = 1_700_000_000
    # Route 6656: direction=0, stop="2836", bus="143"
    feed_bytes = make_feed_bytes(
        trip_id="trip_143",
        route_id="6656",
        direction_id=0,
        stop_id="2836",
        departure_unix=departure_unix,
        delay=120,
    )
    results = await fetch_realtime_schedule(mock_db_session(), mock_http_client(feed_bytes))

    assert len(results) == 1
    r = results[0]
    assert r.route_number == "143"
    assert r.delay_seconds == 120
    assert r.realtime_time == departure_unix
    assert r.scheduled_departure_time == departure_unix - 120


async def test__fetch_realtime_schedule_ignores_wrong_direction():
    # Route 6656 expects direction_id=0; providing 1 should be dropped
    feed_bytes = make_feed_bytes(
        trip_id="trip_143",
        route_id="6656",
        direction_id=1,
        stop_id="2836",
        departure_unix=1_700_000_000,
    )
    results = await fetch_realtime_schedule(mock_db_session(), mock_http_client(feed_bytes))
    assert results == []


async def test__fetch_realtime_schedule_ignores_unknown_route():
    feed_bytes = make_feed_bytes(
        trip_id="trip_999",
        route_id="9999",
        direction_id=0,
        stop_id="9999",
        departure_unix=1_700_000_000,
    )
    results = await fetch_realtime_schedule(mock_db_session(), mock_http_client(feed_bytes))
    assert results == []


async def test__fetch_realtime_schedule_ignores_missing_stop():
    """An entity where the SFU stop doesn't appear in stop_time_update is skipped."""
    feed = gtfs_realtime_pb2.FeedMessage()  # pyright: ignore[reportAttributeAccessIssue]
    feed.header.gtfs_realtime_version = "2.0"
    entity = feed.entity.add()
    entity.id = "e1"
    tu = entity.trip_update
    tu.trip.trip_id = "trip_143"
    tu.trip.route_id = "6656"
    tu.trip.direction_id = 0
    # Add a stop_time_update for a different stop (not "2836")
    stu = tu.stop_time_update.add()
    stu.stop_id = "0000"
    stu.departure.time = 1_700_000_000

    results = await fetch_realtime_schedule(mock_db_session(), mock_http_client(feed.SerializeToString()))
    assert results == []


async def test__fetch_realtime_schedule_empty_feed():
    results = await fetch_realtime_schedule(mock_db_session(), mock_http_client(make_empty_feed_bytes()))
    assert results == []


async def test__fetch_realtime_schedule_sorted_by_time():
    """Results should be sorted by realtime departure time ascending."""
    feed = gtfs_realtime_pb2.FeedMessage()  # pyright: ignore[reportAttributeAccessIssue]
    feed.header.gtfs_realtime_version = "2.0"

    # Two routes with out-of-order times
    entries = [
        ("trip_144", "6657", 1, "12972", 1_700_000_200),
        ("trip_143", "6656", 0, "2836", 1_700_000_100),
    ]
    for i, (tid, rid, did, sid, t) in enumerate(entries):
        e = feed.entity.add()
        e.id = str(i)
        tu = e.trip_update
        tu.trip.trip_id = tid
        tu.trip.route_id = rid
        tu.trip.direction_id = did
        stu = tu.stop_time_update.add()
        stu.stop_id = sid
        stu.departure.time = t

    results = await fetch_realtime_schedule(mock_db_session(), mock_http_client(feed.SerializeToString()))
    assert len(results) == 2
    assert results[0].realtime_time < results[1].realtime_time


async def test__get_or_fetch_realtime_feed_uses_fresh_cache():
    feed_bytes = make_empty_feed_bytes()
    cached_row = TransLinkRealtimeCacheDB(
        id=1,
        fetched_at=datetime.now(tz=TZ_INFO),
        response_bytes=feed_bytes,
    )
    session = mock_db_session(cached_row=cached_row)
    client = AsyncMock(spec=AsyncClient)

    result = await get_or_fetch_realtime_feed(session, client)

    assert result is not None
    assert len(result.entity) == 0
    client.get.assert_not_called()
    session.execute.assert_not_called()
    session.commit.assert_not_called()


async def test__get_or_fetch_realtime_feed_refreshes_stale_cache():
    stale_row = TransLinkRealtimeCacheDB(
        id=1,
        fetched_at=datetime.now(tz=TZ_INFO) - timedelta(seconds=120),
        response_bytes=make_empty_feed_bytes(),
    )
    new_feed_bytes = make_feed_bytes(
        trip_id="trip_143",
        route_id="6656",
        direction_id=0,
        stop_id="2836",
        departure_unix=1_700_000_000,
    )
    session = mock_db_session(cached_row=stale_row)
    client = mock_http_client(new_feed_bytes)

    result = await get_or_fetch_realtime_feed(session, client)

    assert result is not None
    assert len(result.entity) == 1
    client.get.assert_awaited_once()
    session.merge.assert_awaited_once()
    session.commit.assert_awaited_once()


async def test__get_or_fetch_realtime_feed_returns_none_on_http_error_status():
    session = mock_db_session(cached_row=None)
    client = AsyncMock(spec=AsyncClient)
    client.get = AsyncMock(
        return_value=Response(
            status_code=401,
            request=Request("GET", "https://gtfsapi.translink.ca/v3/gtfsrealtime"),
            content=b"Unauthorized",
        )
    )

    result = await get_or_fetch_realtime_feed(session, client)

    assert result is None
    session.merge.assert_not_called()
    session.rollback.assert_awaited_once()


# ---------------------------------------------------------------------------
# Tests for the preprocessed static schedule cache
# ---------------------------------------------------------------------------


async def test__get_static_schedule_cache_hit():
    today = datetime.now(tz=TZ_INFO).date()
    cached_records = [
        {
            "trip_id": "trip_143",
            "route_id": "6656",
            "bus_number": "143",
            "departure_time": "23:00:00",
            "departure_seconds": 82800,
        }
    ]
    cached_row = TransLinkStaticScheduleDB(
        id=1,
        date_fetched=today,
        schedule=make_static_cache(cached_records, today),
    )
    session = mock_db_session(cached_row=cached_row)

    result_date, result_rows = await get_static_schedule(session)

    assert result_date == today
    assert result_rows[0]["bus_number"] == "143"
    session.merge.assert_not_called()
    session.commit.assert_not_called()


async def test__get_static_schedule_cache_miss_raises():
    session = mock_db_session(cached_row=None)

    with pytest.raises(StaticScheduleCacheUnavailableError, match=STATIC_CACHE_UNAVAILABLE_MESSAGE):
        await get_static_schedule(session)

    session.merge.assert_not_called()


async def test__refresh_static_schedule_persists_preprocessed_cache():
    session = mock_db_session(cached_row=None)
    client = mock_http_client(make_gtfs_zip())

    result = await refresh_static_schedule(session, client)

    assert result["version"] == STATIC_CACHE_VERSION
    session.merge.assert_awaited_once()
    session.commit.assert_awaited_once()


async def test__refresh_static_schedule_db_failure_rolls_back():
    import sqlalchemy.exc

    session = mock_db_session(cached_row=None)
    session.merge = AsyncMock(side_effect=sqlalchemy.exc.SQLAlchemyError("disk full"))
    client = mock_http_client(make_gtfs_zip())

    with pytest.raises(RuntimeError, match="Failed to store static schedule"):
        await refresh_static_schedule(session, client)

    session.rollback.assert_awaited_once()
    session.commit.assert_not_called()


async def test__resolve_static_schedule_applies_calendar_exceptions():
    service_date = date(2026, 8, 13)
    date_str = service_date.strftime("%Y%m%d")
    regular = {
        "trip_id": "regular",
        "route_id": "6656",
        "bus_number": "143",
        "departure_time": "10:00:00",
        "departure_seconds": 36000,
    }
    replacement = {**regular, "trip_id": "replacement", "departure_time": "11:00:00", "departure_seconds": 39600}
    cache = make_static_cache([regular], service_date)
    cache["services"]["SPECIAL"] = {
        "start_date": date_str,
        "end_date": date_str,
        "weekdays": [],
    }
    cache["departures"]["SPECIAL"] = [replacement]
    cache["exceptions"][date_str] = {"added": ["SPECIAL"], "removed": ["SVC1"]}

    assert resolve_static_schedule(cache, service_date) == [replacement]


async def test__resolve_static_schedule_rejects_incompatible_version():
    service_date = date(2026, 8, 13)
    cache = make_static_cache([], service_date, version=STATIC_CACHE_VERSION + 1)

    with pytest.raises(StaticScheduleCacheUnavailableError, match=STATIC_CACHE_UNAVAILABLE_MESSAGE):
        resolve_static_schedule(cache, service_date)


async def test__resolve_static_schedule_rejects_malformed_departure():
    service_date = date(2026, 8, 13)
    cache = make_static_cache([{"trip_id": "missing required fields"}], service_date)

    with pytest.raises(StaticScheduleCacheUnavailableError, match=STATIC_CACHE_UNAVAILABLE_MESSAGE):
        resolve_static_schedule(cache, service_date)


async def test__resolve_static_schedule_rejects_date_outside_coverage():
    cache_date = date(2026, 8, 13)
    cache = make_static_cache([], cache_date)

    with pytest.raises(StaticScheduleCacheUnavailableError, match=STATIC_CACHE_UNAVAILABLE_MESSAGE):
        resolve_static_schedule(cache, cache_date + timedelta(days=1))


async def test__get_departure_statuses_uses_timestamps_when_realtime_unavailable():
    now = datetime.now(tz=TZ_INFO)
    midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)
    departure_seconds = int((now - midnight).total_seconds()) + 600
    cached_row = TransLinkStaticScheduleDB(
        id=1,
        date_fetched=now.date(),
        schedule=make_static_cache(
            [
                {
                    "trip_id": "trip_143",
                    "route_id": "6656",
                    "bus_number": "143",
                    "departure_time": "23:00:00",
                    "departure_seconds": departure_seconds,
                }
            ],
            now.date(),
        ),
    )
    session = mock_db_session()
    session.scalar = AsyncMock(side_effect=[cached_row, None, None])
    client = AsyncMock(spec=AsyncClient)
    client.get = AsyncMock(side_effect=httpx.ConnectError("realtime unavailable"))

    result = await get_departure_statuses(session, client)

    expected_timestamp = int((midnight + timedelta(seconds=departure_seconds)).timestamp())
    assert result == [
        TransLinkScheduleResponse(
            route_number="143",
            scheduled_departure_time=expected_timestamp,
            realtime_time=expected_timestamp,
            delay_seconds=0,
            status=BusStatus.OnTime,
        )
    ]


# ---------------------------------------------------------------------------
# REST API endpoint tests
# ---------------------------------------------------------------------------


async def test__endpoint_realtime_returns_200(client):
    mock_response = [
        TransLinkRealtimeResponse(
            route_number="143",
            scheduled_departure_time=1_700_000_000,
            realtime_time=1_700_000_060,
            delay_seconds=60,
        )
    ]
    with patch("translink.urls.fetch_realtime_schedule", return_value=mock_response) as mock_fn:
        response = await client.get("/translink/realtime")

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0]["route_number"] == "143"
    assert data[0]["delay_seconds"] == 60
    mock_fn.assert_awaited_once()


async def test__endpoint_static_returns_schedule(client):
    today = datetime.now(tz=TZ_INFO).date()
    mock_rows = [
        {
            "trip_id": f"trip_{num}",
            "route_id": rid,
            "bus_number": num,
            "departure_time": "23:00:00",
            "departure_seconds": 82800,
        }
        for rid, (_, _, num) in BUS_DATA.items()
    ]
    with patch(
        "translink.urls.get_static_schedule",
        return_value=(today, mock_rows),
    ) as mock_fn:
        response = await client.get("/translink/static")

    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert body["date_fetched"] == today.isoformat()
    assert len(body["schedule"]) == len(BUS_DATA)
    mock_fn.assert_awaited_once()


async def test__endpoint_static_returns_503_when_cache_unavailable(client):
    with patch(
        "translink.urls.get_static_schedule",
        side_effect=StaticScheduleCacheUnavailableError(STATIC_CACHE_UNAVAILABLE_MESSAGE),
    ):
        response = await client.get("/translink/static")

    assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
    assert response.json() == {"detail": STATIC_CACHE_UNAVAILABLE_MESSAGE}


async def test__endpoint_schedule_returns_departure_list(client):
    mock_results = [
        TransLinkScheduleResponse(
            route_number="143",
            scheduled_departure_time=1_700_000_000,
            realtime_time=1_700_000_000,
            delay_seconds=0,
            status=BusStatus.OnTime,
        ),
        TransLinkScheduleResponse(
            route_number="144",
            scheduled_departure_time=1_700_000_600,
            realtime_time=1_700_000_720,
            delay_seconds=120,
            status=BusStatus.Delayed,
        ),
    ]
    with patch("translink.urls.get_departure_statuses", return_value=mock_results) as mock_fn:
        response = await client.get("/translink/schedule")

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 2
    assert data[1]["delay_seconds"] == 120
    mock_fn.assert_awaited_once()


async def test__endpoint_schedule_on_time_when_no_realtime(client):
    """An empty realtime feed (all buses on time) should still return static rows."""
    mock_results = [
        TransLinkScheduleResponse(
            route_number=num,
            scheduled_departure_time=1_700_000_000 + i * 600,
            realtime_time=1_700_000_000 + i * 600,
            delay_seconds=0,
            status=BusStatus.OnTime,
        )
        for i, (_, (_, _, num)) in enumerate(BUS_DATA.items())
    ]
    with patch("translink.urls.get_departure_statuses", return_value=mock_results):
        response = await client.get("/translink/schedule")

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert all(d["delay_seconds"] == 0 for d in data)


async def test__endpoint_schedule_returns_503_when_cache_unavailable(client):
    with patch(
        "translink.urls.get_departure_statuses",
        side_effect=StaticScheduleCacheUnavailableError(STATIC_CACHE_UNAVAILABLE_MESSAGE),
    ):
        response = await client.get("/translink/schedule")

    assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
    assert response.json() == {"detail": STATIC_CACHE_UNAVAILABLE_MESSAGE}
