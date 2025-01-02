from dataclasses import dataclass


class SessionType:
    # see: https://www.sfu.ca/information-systems/services/cas/cas-for-web-applications/
    # for more info on the kinds of members
    FACULTY = "faculty"
    # TODO: what will happen to the maillists for authentication; are groups part of this?
    CSSS_MEMBER = "csss member" # !cs-students maillist
    STUDENT = "student"
    ALUMNI = "alumni"
    SFU = "sfu"

@dataclass
class SiteUserData:
    computing_id: str
    first_logged_in: str
    last_logged_in: str
    profile_picture_url: None | str

    def serializable_dict(self):
        return {
            "computing_id": self.computing_id,
            "first_logged_in": self.first_logged_in,
            "last_logged_in": self.last_logged_in,
            "profile_picture_url": self.profile_picture_url
        }
