from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date, datetime

from constants import COMPUTING_ID_MAX
from fastapi import HTTPException

from officers.constants import OfficerPosition
from officers.tables import OfficerInfo, OfficerTerm


@dataclass
class OfficerInfoUpload:
    # TODO: compute this using SFU's API; if unable, use a default value
    legal_name: str
    phone_number: None | str = None
    discord_name: None | str = None
    github_username: None | str = None
    google_drive_email: None | str = None

    def validate(self) -> None | HTTPException:
        if self.legal_name is not None and self.legal_name == "":
            return HTTPException(status_code=400, detail="legal name must not be empty")
        # TODO: more checks
        else:
            return None

    def to_officer_info(self, computing_id: str, discord_id: str | None, discord_nickname: str | None) -> OfficerInfo:
        return OfficerInfo(
            computing_id = computing_id,
            legal_name = self.legal_name,

            discord_id = discord_id,
            discord_name = self.discord_name,
            discord_nickname = discord_nickname,

            phone_number = self.phone_number,
            github_username = self.github_username,
            google_drive_email = self.google_drive_email,
        )

    def to_update_dict(self) -> dict:
        return {
            # TODO: if the API call to SFU's api to get legal name fails, we want to fail & not insert the entry.
            # for now, we should insert a default value
            "legal_name": "default name" if self.legal_name is None else self.legal_name,

            "discord_id": self.discord_id,
            "discord_name": self.discord_name,
            "discord_nickname": self.discord_nickname,

            "phone_number": self.phone_number,
            "github_username": self.github_username,
            "google_drive_email": self.google_drive_email,
        }

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
        elif self.position not in OfficerPosition.position_list():
            raise HTTPException(status_code=400, detail=f"invalid position={self.position}")
        # TODO: more checks
        # TODO: how to check this one? make sure date is date & not datetime?
        #elif not is_iso_format(self.start_date):
        #    raise HTTPException(status_code=400, detail=f"start_date={self.start_date} must be a valid iso date")
        else:
            return None

    def to_officer_term(self) -> OfficerTerm:
        return OfficerTerm(
            computing_id = self.computing_id,

            position = self.position,
            start_date = self.start_date,
            end_date = self.end_date,

            nickname = self.nickname,
            favourite_course_0 = self.favourite_course_0,
            favourite_course_1 = self.favourite_course_1,
            favourite_pl_0 = self.favourite_pl_0,
            favourite_pl_1 = self.favourite_pl_1,
            biography = self.biography,
            photo_url = self.photo_url,
        )

    def update_dict(self) -> dict:
        # TODO: control this by term_id & allow the others to be updated
        # cannot update:
        # - computing_id
        # - start_date
        # - position
        return {
            "end_date": self.end_date,
            "nickname": self.nickname,

            "favourite_course_0": self.favourite_course_0,
            "favourite_course_1": self.favourite_course_1,
            "favourite_pl_0": self.favourite_pl_0,
            "favourite_pl_1": self.favourite_pl_1,

            "biography": self.biography,
            "photo_url": self.photo_url,
        }

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

    @staticmethod
    def from_data(
        term: officers.tables.OfficerTerm,
        officer_info: officers.tables.OfficerInfo,
        include_private: bool,
        is_active: bool,
    ) -> OfficerData:
        return OfficerData(
            is_active = is_active,

            position = term.position,
            start_date = term.start_date,
            end_date = term.end_date,

            legal_name = officer_info.legal_name,
            nickname = term.nickname,
            discord_name = officer_info.discord_name,
            discord_nickname = officer_info.discord_nickname,

            favourite_course_0 = term.favourite_course_0,
            favourite_course_1 = term.favourite_course_1,
            favourite_language_0 = term.favourite_pl_0,
            favourite_language_1 = term.favourite_pl_1,

            csss_email = OfficerPosition.to_email(term.position),
            biography = term.biography,
            photo_url = term.photo_url,

            private_data = OfficerPrivateData(
                computing_id = term.computing_id,
                phone_number = officer_info.phone_number,
                github_username = officer_info.github_username,
                google_drive_email = officer_info.google_drive_email,
            ) if include_private else None,
        )
