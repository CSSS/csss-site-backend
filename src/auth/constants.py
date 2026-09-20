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
    """
    Roles defined for site users. Some of it is hierarchical, some of them give permissions to certain resources.

    Attributes:
        ACCESS: Can manage everything.
        ADMIN: Can manage everything except admin status.
        EXEC: Can view private officer info, events, honorary members, and upload media. Can't see any election material or make changes to anything.
        OFFICER: A non-executive that has been tasked to do something and requires elevated permission e.g. Elections Officer.
        USER: Base user, does not have permissions for anything at the moment.

        EVENT: Can view and manage events.
        ELECTION: Can view and manage elections.
    """

    # Hierarchical roles
    ACCESS = "access"
    ADMIN = "admin"
    EXEC = "exec"
    OFFICER = "officer"
    USER = "user"

    # Access roles for specific features
    EVENT = "event"
    ELECTION = "election"
