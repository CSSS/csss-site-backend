import os
import pathlib

# this google account runs the google workspace for executives
GOOGLE_WORKSPACE_ACCOUNT = "csss@sfucsss.org"

# any officer from the past 5 semesters has access to these
# TODO: ask the pres if we still want these rules, or not
FIVE_SEM_OFFICER_ACCESS = [
    "CSSS@SFU",
]

EXECUTIVE_ACCESS = [
    "CSSS Gallery",
    "CSSS@SFU",
    "Deep-Exec",
    "Exec_Photos",
    "Private Gallery",
]

# scopes are like permissions to google
GOOGLE_API_SCOPES = [
    # google drive permission
    "https://www.googleapis.com/auth/drive"
]

GOOGLE_DRIVE_PERMISSION_ROLES = [
    "organizer",
    "fileOrganizer",
]

_this_file_path = pathlib.Path(__file__).parent.resolve()
SERVICE_ACCOUNT_KEY_PATH = str((_this_file_path / "../../google_key.json").resolve())
