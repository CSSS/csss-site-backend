# TransLink API Documentation
This is supporting documentation for the TransLink API our server uses.
This server only filters for the buses that begin/end at the upper bus loop at SFU Burnaby campus which are: 143, 144, 145, and R5.
All dates are adjusted for the America/Vancouver timezone.

## Quickstart
1. You need an API key to do anything with realtime data. You can sign up for one [here](https://www.translink.ca/about-us/doing-business-with-translink/app-developer-resources/register
2. Put the API key in `src/.env` with the key `TRANSLINK_API_KEY=<your API key>` or create an environment variable `export TRANSLINK_API_KEY=<your api key>`.
3. Make sure your database has the correct migrations `alembic upgrade head`. Reload your test database as well `python src/load_test_db.py`
4. Start (or restart) the web server to test the endpoints

## Endpoints
You can see the exact schemas in the `/docs` page. At the time this was written there are three endpoints:
1. `translink/realtime`: returns realtime data for buses that are at or are approaching SFU
2. `translink/static`: returns the schedule for the current day
3. `translink/schedule`: combines the realtime and static data to show if a bus is at the loop, is running late, or was cancelled
