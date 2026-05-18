import io
import zipfile
from datetime import date, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pandas as pd
import pytest
from fastapi import status
from google.transit import gtfs_realtime_pb2
from httpx import AsyncClient, Response

from constants import TZ_INFO
from translink.crud import (
    BUS_DATA,
    _gtfs_time_to_seconds,
    fetch_realtime_schedule,
    fetch_static_schedule,
    get_next_departures,
    get_or_fetch_static_schedule,
)
from translink.models import BusStatus, TransLinkRealtimeResponse, TransLinkScheduleResponse
from translink.tables import TransLinkStaticScheduleDB

pytestmark = pytest.mark.asyncio(loop_scope="session")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _current_day_name() -> str:
    return datetime.now(tz=TZ_INFO).strftime("%A").lower()


def make_gtfs_zip(departure_time: str = "23:00:00") -> bytes:
    """
    Return a minimal but valid GTFS zip whose single service is active today,
    with one trip per route in BUS_DATA.

    `departure_time` is used for all stop_times rows — set it in the future
    (the default "23:00:00" works for most of the day) so get_next_departures
    includes them.
    """
    buf = io.BytesIO()
    day = _current_day_name()
    all_days = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]

    with zipfile.ZipFile(buf, "w") as z:
        # calendar.txt - one service active only on today's weekday
        cal_row = {d: ("1" if d == day else "0") for d in all_days}
        cal_row.update({"service_id": "SVC1", "start_date": "20240101", "end_date": "20991231"})
        z.writestr("calendar.txt", pd.DataFrame([cal_row]).to_csv(index=False))

        # calendar_dates.txt - no exceptions
        z.writestr("calendar_dates.txt", "date,service_id,exception_type\n")

        # trips.txt - one trip per (route_id, direction_id) pair in BUS_DATA
        trips_rows = [
            {"trip_id": f"trip_{num}", "route_id": rid, "service_id": "SVC1", "direction_id": str(did)}
            for rid, (did, _sid, num) in BUS_DATA.items()
        ]
        z.writestr("trips.txt", pd.DataFrame(trips_rows).to_csv(index=False))

        # stop_times.txt - one stop per trip at the correct SFU bus loop stop
        stop_rows = [
            {"trip_id": f"trip_{num}", "stop_id": sid, "departure_time": departure_time}
            for _rid, (_, sid, num) in BUS_DATA.items()
        ]
        z.writestr("stop_times.txt", pd.DataFrame(stop_rows).to_csv(index=False))

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

    schedule = pd.DataFrame(
        [
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
    )

    result = get_next_departures(schedule, n=3)
    assert len(result) == 1
    assert result.iloc[0]["trip_id"] == "future_trip"


async def test__get_next_departures_respects_n():
    now = datetime.now(tz=TZ_INFO)
    midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)
    now_secs = int((now - midnight).total_seconds())

    # Five future trips on the same route - n=2 should limit to 2
    schedule = pd.DataFrame(
        [
            {
                "trip_id": f"trip_{i}",
                "route_id": "6656",
                "bus_number": "143",
                "departure_time": "23:00:00",
                "departure_seconds": now_secs + i * 600,
            }
            for i in range(1, 6)
        ]
    )

    assert len(get_next_departures(schedule, n=2)) == 2
    assert len(get_next_departures(schedule, n=1)) == 1


async def test__get_next_departures_multiple_routes():
    now = datetime.now(tz=TZ_INFO)
    midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)
    now_secs = int((now - midnight).total_seconds())

    schedule = pd.DataFrame(
        [
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
    )

    result = get_next_departures(schedule, n=2)
    assert len(result) == 8
    assert set(result["route_id"]) == set(BUS_DATA.keys())


# ---------------------------------------------------------------------------
# Tests for fetch_static_schedule
# ---------------------------------------------------------------------------


async def test__fetch_static_schedule_returns_all_routes():
    client = mock_http_client(make_gtfs_zip())
    df = await fetch_static_schedule(client)

    assert not df.empty
    expected_cols = {"trip_id", "route_id", "bus_number", "departure_time", "departure_seconds"}
    assert expected_cols.issubset(df.columns)
    assert set(df["bus_number"]) == {num for _, (_, _, num) in BUS_DATA.items()}


async def test__fetch_static_schedule_excludes_wrong_direction():
    """Trips are direction-filtered; a wrong-direction trip should not appear."""
    buf = io.BytesIO()
    day = _current_day_name()
    all_days = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]

    with zipfile.ZipFile(buf, "w") as z:
        cal_row = {d: ("1" if d == day else "0") for d in all_days}
        cal_row.update({"service_id": "SVC1", "start_date": "20240101", "end_date": "20991231"})
        z.writestr("calendar.txt", pd.DataFrame([cal_row]).to_csv(index=False))
        z.writestr("calendar_dates.txt", "date,service_id,exception_type\n")

        # Route 6656 expects direction_id=0; give it direction_id=1
        trips_df = pd.DataFrame(
            [
                {"trip_id": "wrong_dir", "route_id": "6656", "service_id": "SVC1", "direction_id": "1"},
            ]
        )
        z.writestr("trips.txt", trips_df.to_csv(index=False))
        z.writestr(
            "stop_times.txt",
            pd.DataFrame([{"trip_id": "wrong_dir", "stop_id": "2836", "departure_time": "23:00:00"}]).to_csv(
                index=False
            ),
        )

    client = mock_http_client(buf.getvalue())
    df = await fetch_static_schedule(client)
    assert df.empty


async def test__fetch_static_schedule_raises_on_http_error():
    import httpx

    client = AsyncMock(spec=AsyncClient)
    client.get = AsyncMock(side_effect=httpx.HTTPError("connection refused"))

    with pytest.raises(RuntimeError, match="Failed to fetch static schedule"):
        await fetch_static_schedule(client)


async def test__fetch_static_schedule_raises_on_bad_zip():
    client = mock_http_client(b"this is not a zip")

    with pytest.raises(RuntimeError, match="Failed to read static schedule zip file"):
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
    results = await fetch_realtime_schedule(mock_http_client(feed_bytes))

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
    results = await fetch_realtime_schedule(mock_http_client(feed_bytes))
    assert results == []


async def test__fetch_realtime_schedule_ignores_unknown_route():
    feed_bytes = make_feed_bytes(
        trip_id="trip_999",
        route_id="9999",
        direction_id=0,
        stop_id="9999",
        departure_unix=1_700_000_000,
    )
    results = await fetch_realtime_schedule(mock_http_client(feed_bytes))
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

    results = await fetch_realtime_schedule(mock_http_client(feed.SerializeToString()))
    assert results == []


async def test__fetch_realtime_schedule_empty_feed():
    results = await fetch_realtime_schedule(mock_http_client(make_empty_feed_bytes()))
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

    results = await fetch_realtime_schedule(mock_http_client(feed.SerializeToString()))
    assert len(results) == 2
    assert results[0].realtime_time < results[1].realtime_time


# ---------------------------------------------------------------------------
# Tests for get_or_fetch_static_schedule
# ---------------------------------------------------------------------------


async def test__get_or_fetch_static_schedule_cache_hit():
    """When the DB has today's row, no HTTP call should be made."""
    cached_records = [
        {
            "trip_id": "trip_143",
            "route_id": "6656",
            "bus_number": "143",
            "departure_time": "23:00:00",
            "departure_seconds": 82800,
        }
    ]
    cached_row = TransLinkStaticScheduleDB(id=1, date_fetched=date.today(), schedule=cached_records)
    session = mock_db_session(cached_row=cached_row)
    client = AsyncMock(spec=AsyncClient)

    result_date, result_df = await get_or_fetch_static_schedule(session, client)

    assert result_date == date.today()
    assert not result_df.empty
    assert result_df.iloc[0]["bus_number"] == "143"
    client.get.assert_not_called()


async def test__get_or_fetch_static_schedule_cache_miss_fetches():
    """On a cache miss the function should call the API and persist the result."""
    session = mock_db_session(cached_row=None)
    client = mock_http_client(make_gtfs_zip())

    result_date, result_df = await get_or_fetch_static_schedule(session, client)

    assert result_date == date.today()
    assert not result_df.empty
    session.merge.assert_awaited_once()
    session.commit.assert_awaited_once()


async def test__get_or_fetch_static_schedule_db_write_failure_still_returns():
    """If the DB write fails, the function should still return the fetched data."""
    import sqlalchemy.exc

    session = mock_db_session(cached_row=None)
    session.merge = AsyncMock(side_effect=sqlalchemy.exc.SQLAlchemyError("disk full"))
    client = mock_http_client(make_gtfs_zip())

    result_date, result_df = await get_or_fetch_static_schedule(session, client)

    assert result_date == date.today()
    assert not result_df.empty
    session.rollback.assert_awaited_once()


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
    today = date.today()
    mock_df = pd.DataFrame(
        [
            {
                "trip_id": f"trip_{num}",
                "route_id": rid,
                "bus_number": num,
                "departure_time": "23:00:00",
                "departure_seconds": 82800,
            }
            for rid, (_, _, num) in BUS_DATA.items()
        ]
    )
    with patch(
        "translink.urls.get_or_fetch_static_schedule",
        return_value=(today, mock_df),
    ) as mock_fn:
        response = await client.get("/translink/static")

    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert body["date_fetched"] == today.isoformat()
    assert len(body["schedule"]) == len(BUS_DATA)
    mock_fn.assert_awaited_once()


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
