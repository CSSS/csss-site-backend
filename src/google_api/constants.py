import os
import pathlib

_this_file_path = pathlib.Path(__file__).parent.resolve()

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

GOOGLE_API_SCOPES = [
    "https://www.googleapis.com/auth/drive"
]

SERVICE_ACCOUNT_KEY_PATH = str((_this_file_path / "../../google_key.json").resolve())
