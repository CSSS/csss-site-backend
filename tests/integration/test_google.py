from google_api import internals


# NOTE: must perform setup as described in the csss-site-backend wiki
def test__list_drives():
    """should not fail"""
    drive_list = internals._list_shared_drives()
    print(drive_list)

    drive_id = drive_list["drives"][0]["id"]
    print(drive_id)

    permissions = internals.list_drive_permissions(drive_id)
    print(permissions)

    # NOTE: this will raise an exception if the email address is a non-google account
    """
    internals.create_drive_permission(
        drive_id,
        {
            "type": "user",
            "emailAddress": "tester_123591735013000019@gmail2.ca",
            "role": "fileOrganizer",
        }
    )
    """
