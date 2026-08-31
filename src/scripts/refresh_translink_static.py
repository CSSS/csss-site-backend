"""Download, preprocess, and store the TransLink static GTFS schedule."""

import asyncio
import logging

import httpx

import database
from translink.crud import refresh_static_schedule

_logger = logging.getLogger(__name__)


async def refresh() -> None:
    await database.setup_database()
    if database.sessionmanager is None:
        raise RuntimeError("Database has not been initialized")

    manager = database.sessionmanager
    try:
        async with httpx.AsyncClient(timeout=60, follow_redirects=True) as client:
            async with manager.session() as session:
                cache = await refresh_static_schedule(session, client)
        departure_count = sum(len(rows) for rows in cache["departures"].values())
        _logger.info(
            "Stored TransLink static schedule version %s with %s departures covering %s through %s",
            cache["version"],
            departure_count,
            cache["coverage"]["start_date"],
            cache["coverage"]["end_date"],
        )
    finally:
        await manager.close()


def main() -> int:
    logging.basicConfig(level=logging.INFO)
    try:
        asyncio.run(refresh())
    except Exception:
        _logger.exception("Failed to refresh the TransLink static schedule")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
