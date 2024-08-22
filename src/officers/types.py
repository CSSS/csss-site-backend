import json
from dataclasses import asdict, dataclass
from datetime import date, datetime

from constants import COMPUTING_ID_MAX
from fastapi import HTTPException
from utils import is_iso_format

from officers.constants import OfficerPosition

# TODO: leave the following, but create one for current_officers private info & non-private info
# make it so that the docs shows the expected return schema

# TODO: are any of these nullable? Not sure yet...
@dataclass
class OfficerInfoData:
    computing_id: str

    legal_name: str
    discord_id: None | str = None # TODO: do we need this to get info about a person
    discord_name: None | str = None
    discord_nickname: None | str = None

    phone_number: None | str = None
    github_username: None | str = None
    google_drive_email: None | str = None

    def validate(self) -> None | HTTPException:
        if len(self.computing_id) > COMPUTING_ID_MAX:
            return HTTPException(status_code=400, detail=f"computing_id={self.computing_id} is too large")
        elif self.legal_name is not None and self.legal_name == "":
            return HTTPException(status_code=400, detail="legal name must not be empty")
        # TODO: more checks
        else:
            return None


@dataclass
class OfficerTermData:
    computing_id: str

    position: str
    start_date: date
    end_date: None | date = None

    nickname: None | str = None
    favourite_course_0: None | str = None
    favourite_course_1: None | str = None
    favourite_pl_0: None | str = None
    favourite_pl_1: None | str = None
    biography: None | str = None

    # TODO: we're going to need an API call to upload images
    # NOTE: changing the name of this variable without changing all instances is breaking
    photo_url: None | str = None

    def validate(self) -> None | HTTPException:
        if len(self.computing_id) > COMPUTING_ID_MAX:
            return HTTPException(status_code=400, detail=f"computing_id={self.computing_id} is too large")
        elif self.position not in OfficerPosition.position_values():
            raise HTTPException(status_code=400, detail=f"invalid position={self.position}")
        # TODO: more checks
        # TODO: how to check this one? make sure date is date & not datetime?
        #elif not is_iso_format(self.start_date):
        #    raise HTTPException(status_code=400, detail=f"start_date={self.start_date} must be a valid iso date")
        else:
            return None

# -------------------------------------------- #

@dataclass
class OfficerPrivateData:
    computing_id: str | None
    phone_number: str | None
    github_username: str | None
    google_drive_email: str | None

@dataclass
class OfficerData:
    is_active: bool

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

    csss_email: str | None
    biography: str | None
    photo_url: str | None  # some urls get big...

    private_data: OfficerPrivateData | None

    def serializable_dict(self):
        # we need to manually serialize datetime objects for some reason...
        new_self = asdict(self)
        new_self["start_date"] = new_self["start_date"].isoformat()
        if new_self["end_date"] is not None:
            new_self["end_date"] = new_self["end_date"].isoformat()
        return new_self
