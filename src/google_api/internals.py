# google workspace (shared drives) + google drive api

import io
import os

import requests
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
from requests import Response

from google_api.constants import GOOGLE_API_SCOPES, SERVICE_ACCOUNT_KEY_PATH

# TODO: understand how these work
credentials = service_account.Credentials.from_service_account_file(
    filename=SERVICE_ACCOUNT_KEY_PATH,
    scopes=GOOGLE_API_SCOPES
)
delegated_credentials = credentials.with_subject("csss@sfucsss.org")
service = build("drive", "v3", credentials=delegated_credentials)

# TODO: view access to root folders / organization
# TODO: give access to root folders / organization

# TODO: how to even do this correctly?
def _get_access_token() -> str:
    pass

def _google_drive_request(
    url: str,
    token: str, # TODO: what kind of token is it?
) -> Response:
    result = requests.get(
        url,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }
    )
    return result

def _list_shared_drives(token: str):
    response = _google_drive_request(
        "https://www.googleapis.com/drive/v3/drives?",
        token
    )
    return str(response)

def _list_shared_drives_2():
    # Call the Drive v3 API
    # TODO: see if we can make API calls directly without this funky stuff... ?
    results = (
        service
        .drives()
        .list(
            #pageSize = 50,
            #q = "name contains 'CSSS'",
            #useDomainAdminAccess = True,
        )
        .execute()
    )

    # get the results
    print(results)

def is_email_valid():
    # TODO: determine if a google email is valid
    pass
