# google workspace (shared drives) + google drive api

from google.oauth2 import service_account
from googleapiclient.discovery import build

from google_api.constants import GOOGLE_API_SCOPES, GOOGLE_WORKSPACE_ACCOUNT, SERVICE_ACCOUNT_KEY_PATH

# TODO: understand how these work
credentials = service_account.Credentials.from_service_account_file(
    filename=SERVICE_ACCOUNT_KEY_PATH,
    scopes=GOOGLE_API_SCOPES
)
delegated_credentials = credentials.with_subject(GOOGLE_WORKSPACE_ACCOUNT)
service = build("drive", "v3", credentials=delegated_credentials)

def _list_shared_drives() -> list:
    return (
        service
        .drives()
        .list(
            #pageSize = 50,
            #q = "name contains 'CSSS'",
            #useDomainAdminAccess = True,
        )
        .execute()
    )

def list_drive_permissions(drive_id: str) -> list:
    return (
        service
        .permissions()
        .list(
            fileId = drive_id,
            # important to find the shared drive
            supportsAllDrives = True,
            fields = "*",
        )
        .execute()
    )

def create_drive_permission(drive_id: str, permission: dict):
    return (
        service
        .permissions()
        .create(
            fileId = drive_id,

            # TODO: update message
            emailMessage = "You were just given permission to an SFU CSSS shared google drive!",
            sendNotificationEmail = True,
            supportsAllDrives = True,

            body=permission,
        )
        .execute()
    )

def delete_drive_permission(drive_id: str, permission_id: str):
    return (
        service
        .permissions()
        .delete(
            fileId = drive_id,
            permissionId = permission_id,
            supportsAllDrives = True,
        )
        .execute()
    )
