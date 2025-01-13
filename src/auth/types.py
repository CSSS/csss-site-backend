from dataclasses import dataclass


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
