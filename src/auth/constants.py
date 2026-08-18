from datetime import timedelta
from enum import StrEnum

from config import settings

CAS_LOGIN_URL = "https://cas.sfu.ca/cas/login"
CAS_VALIDATE_URL = "https://cas.sfu.ca/cas/serviceValidate"

COOKIE_AUTH_REDIRECT_KEY = "auth_redirect"
COOKIE_SESSION_KEY = "__Secure-csss_session" if settings.cookie_secure else "csss_session"
COOKIE_PATH = "/"
COOKIE_MAX_AGE = 60 * 60 * 2  # 2 hours in seconds
COOKIE_SAMESITE = "lax"

SESSION_MAX_AGE = timedelta(seconds=COOKIE_MAX_AGE)

REDIRECT_TTL = 60 * 5  # 5 minutes in seconds

SITE_USER_ROLE_MAX_LENGTH = 32  # Max length of a user permission string


class UserRole(StrEnum):
    ADMIN = "admin"  # Highest level, can manage pretty much everything
    EXEC = "exec"  # Allowed to upload media, documents, etc.
    USER = "user"  # Lowest level, can only access basic functionality
