from datetime import timedelta

COOKIE_SESSION_KEY = "session_id"
COOKIE_MAX_AGE = 60 * 60 * 2  # 2 hours in seconds
SESSION_MAX_AGE = timedelta(seconds=COOKIE_MAX_AGE)
