from datetime import timedelta

from config import settings

CAS_LOGIN_URL = "https://cas.sfu.ca/cas/login"
CAS_VALIDATE_URL = "https://cas.sfu.ca/cas/serviceValidate"
COOKIE_AUTH_REDIRECT_KEY = "auth_redirect"
COOKIE_SESSION_KEY = "__Secure-csss_session" if settings.cookie_secure else "csss_session"
COOKIE_PATH = "/"
COOKIE_MAX_AGE = 60 * 60 * 2  # 2 hours in seconds
SESSION_MAX_AGE = timedelta(seconds=COOKIE_MAX_AGE)

COOKIE_SAMESITE = "lax"
REDIRECT_TTL = 60 * 5  # 5 minutes in seconds
