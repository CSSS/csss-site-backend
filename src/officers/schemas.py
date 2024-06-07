from datetime import datetime

from pydantic import BaseModel

# TODO: leave the following, but create one for current_officers private info & non-private info
# make it so that the docs shows the expected return schema

"""
# TODO: add structs for returning data from the other api calls

class OfficerPrivateData_Download(BaseModel):
    computing_id: str | None
    phone_number: str | None
    github_username: str | None
    google_drive_email: str | None

    class Config:
        orm_mode = True


class OfficerPublicData_Download(BaseModel):
    is_current_officer: bool

    # an officer may have multiple positions, such as FroshWeekChair & DirectorOfEvents
    position: str
    start_date: datetime
    end_date: datetime | None

    legal_name: str  # some people have long names, you never know
    nickname: str | None
    discord_name: str | None
    discord_nickname: str | None

    favourite_course_0: str | None
    favourite_course_1: str | None

    favourite_language_0: str | None
    favourite_language_1: str | None

    sfu_email: str | None
    biography: str | None
    photo_url: str | None  # some urls get big...

    private_data: OfficerPrivateData_Download | None

    class Config:
        orm_mode = True


# the data that has to be provided when a new officer is created
class NewOfficerData_Upload(BaseModel):
    position: str
    computing_id: str
    start_date: datetime


# Personal data that has to be uploaded by a new officer themselves.
# Only stored once.
class OfficerPersonalData_Upload(BaseModel):
    assignment_id: str  # NOTE: the user will be able to choose which assignment they want to upload data for by accessing another API call using their token which they've received from authenticating. The website knows every user's computing_id.

    legal_name: str | None
    discord_id: str | None
    discord_name: str | None

    phone_number: str | None
    github_username: str | None
    google_drive_email: str | None

    class Config:
        orm_mode = True


# the data that has to be uploaded by a new officer themselves
# stored for every new exec term
class OfficerPositionData_Upload(BaseModel):
    assignment_id: str  # NOTE: the user will be able to choose which assignment they want to upload data for by accessing another API call using their token which they've received from authenticating. The website knows every user's computing_id.

    nickname: str | None

    favourite_course_0: str | None
    favourite_course_1: str | None

    favourite_language_0: str | None
    favourite_language_1: str | None

    biography: str | None
    photo_url: str | None  # some urls get big...
"""

"""
# TODO: this is for another api call, where the doa should be able to change any aspect of the person's configuration, just in case
class OfficerDataUpdate_Upload(BaseModel):
    is_current_officer: bool

    # an officer may have multiple positions, such as FroshWeekChair & DirectorOfEvents
    position: str
    start_date: datetime
    end_date: datetime | None

    legal_name: str # some people have long names, you never know
    nickname: str | None
    discord_name: str | None
    discord_nickname: str | None

    favourite_course_0: str | None
    favourite_course_1: str | None

    favourite_language_0: str | None
    favourite_language_1: str | None

    sfu_email: str | None
    biography: str | None
    photo_url: str | None # some urls get big...

    private_data: OfficerPrivateData_Download | None
"""