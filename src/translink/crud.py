import io
import zipfile
from datetime import datetime
from typing import cast

import pandas as pd
from httpx import AsyncClient

from constants import TZ_INFO

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


def _get_active_service_ids(z: zipfile.ZipFile) -> set[str]:
    today = datetime.now(tz=TZ_INFO)
    # Dates in the calendar.txt are in YYYYMMDD
    date_str = today.strftime("%Y%m%d")
    day_name = today.strftime("%A").lower()

    calendar = pd.read_csv(z.open("calendar.txt"), dtype=str)
    active = set(
        calendar[
            (calendar[day_name] == "1") & (calendar["start_date"] <= date_str) & (calendar["end_date"] >= date_str)
        ]["service_id"]
    )

    # These are exceptions to services in the calendar
    # exception_type=1 means service was added
    # exception_type=2 means service was removed
    exceptions = pd.read_csv(z.open("calendar_dates.txt"), dtype=str)
    added = exceptions[(exceptions["date"] == date_str) & (exceptions["exception_type"] == "1")]["service_id"]
    removed = exceptions[(exceptions["date"] == date_str) & (exceptions["exception_type"] == "2")]["service_id"]
    active |= set(added)
    active -= set(removed)
    return active


async def fetch_static_schedule(client: AsyncClient) -> pd.DataFrame:
    """
    Gets the static bus schedule from the static TransLink GTFS API
    """
    # Retrieve the static TransLink bus schedule data
    static_response = await client.get("https://gtfs-static.translink.ca/gtfs/google_transit.zip")
    z = zipfile.ZipFile(io.BytesIO(static_response.content))

    # A trip is from one stop to the next one
    active_services = _get_active_service_ids(z)
    trips = pd.read_csv(z.open("trips.txt"), dtype=str)
    # Stop times contain when the bus should depart a bus stop
    stop_times = pd.read_csv(z.open("stop_times.txt"), dtype=str)

    # From all the active trips, only get the ones that go to the bus loop
    route_ids = set(BUS_DATA.keys())
    filtered_trips = trips[trips["route_id"].isin(list(route_ids)) & trips["service_id"].isin(list(active_services))]
    filtered_trips = filtered_trips[
        filtered_trips.apply(lambda row: int(row["direction_id"]) == BUS_DATA[row["route_id"]][0], axis=1)
    ]

    # Get the stop times entries for the stops at the bus loop
    stop_ids = {s[1] for s in BUS_DATA.values()}
    stop_times = stop_times[
        stop_times["trip_id"].isin(list(filtered_trips["trip_id"])) & stop_times["stop_id"].isin(list(stop_ids))
    ]

    # Join the data from the trips and the stops
    # Casts are done to avoid some typing issues, but they might be unnecessary
    merged = stop_times.merge(cast(pd.DataFrame, filtered_trips[["trip_id", "route_id"]]), on="trip_id")  # cross join
    merged = cast(
        pd.DataFrame, merged[merged.apply(lambda row: row["stop_id"] == BUS_DATA[row["route_id"]][1], axis=1)]
    )  # filter for the stops we care about

    merged = merged.copy()  # stops pandas from complaining about modifying original data
    merged["bus_number"] = merged["route_id"].map(lambda r: BUS_DATA[r][2])
    merged["departure_seconds"] = merged["departure_time"].map(_gtfs_time_to_seconds)

    return cast(
        pd.DataFrame,
        merged[["trip_id", "route_id", "bus_number", "departure_seconds"]].reset_index(drop=True),
    )


def get_next_departures(schedule: pd.DataFrame, n: int = 3) -> pd.DataFrame:
    """
    Get the next few departures for today.

    Args:
        schedule: static schedule filtered out for the relevant routes
        n: the number of departures to get for each route

    Returns:
        A dataframe with the next n departures for each route, sorted by route ID and departure time (in seconds).
    """
    now = datetime.now(tz=TZ_INFO)
    current_seconds = int((now - now.replace(hour=0, minute=0, second=0, microsecond=0)).total_seconds())
    upcoming = cast(pd.DataFrame, schedule[schedule["departure_seconds"] > current_seconds])
    return (
        upcoming.sort_values("departure_seconds")
        .groupby("route_id")
        .head(n)
        .sort_values(["route_id", "departure_seconds"])
    )
