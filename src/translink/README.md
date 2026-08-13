# TransLink API Documentation
This is supporting documentation for the TransLink API our server uses.
This server only filters for the buses that begin/end at the upper bus loop at SFU Burnaby campus which are: 143, 144, 145, and R5.
All dates are adjusted for the America/Vancouver timezone.

## Quickstart
1. You need an API key to do anything with realtime data. You can sign up for one [here](https://www.translink.ca/about-us/doing-business-with-translink/app-developer-resources/register
2. Put the API key in `src/.env` with the key `TRANSLINK_API_KEY=<your API key>` or create an environment variable `export TRANSLINK_API_KEY=<your api key>`.
3. Make sure your database has the correct migrations `alembic upgrade head`. Reload your test database as well `python src/load_test_db.py`
4. Start (or restart) the web server to test the endpoints

## Static schedule refresh

The static GTFS archive is downloaded and preprocessed outside HTTP requests. Before serving the static schedule for
the first time, populate the cache manually from the `src` directory:

```bash
# in ./src
uv run python -m scripts.refresh_translink_static
```

If deploying on the web server run the cron job.
```bash
# in root
sh config/cron.sh
```
Production refreshes it every Friday at 11:00 PM in the America/Vancouver timezone. Install or update that cron entry
by running `sh config/cron.sh` from the repository root. The installer is idempotent.

If a refresh fails, the prior database row is preserved and the command exits unsuccessfully. If no compatible cache
can serve the current date, the static and combined schedule endpoints return HTTP 503; requests never download or
parse the static GTFS archive.

## Endpoints
You can see the exact schemas in the `/docs` page. At the time this was written there are three endpoints:
1. `translink/realtime`: returns realtime data for buses that are at or are approaching SFU
2. `translink/static`: returns the preprocessed schedule for the current day
3. `translink/schedule`: combines the realtime and static data to show if a bus is at the loop, is running late, or was cancelled
