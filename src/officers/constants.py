from enum import StrEnum

# OFFICER FIELD CONSTRAINTS
OFFICER_POSITION_MAX = 128
OFFICER_LEGAL_NAME_MAX = 128


class OfficerPositionEnum(StrEnum):
    PRESIDENT = "president"
    VICE_PRESIDENT = "vice-president"
    TREASURER = "treasurer"

    DIRECTOR_OF_RESOURCES = "director of resources"
    DIRECTOR_OF_EVENTS = "director of events"
    DIRECTOR_OF_EDUCATIONAL_EVENTS = "director of educational events"
    ASSISTANT_DIRECTOR_OF_EVENTS = "assistant director of events"
    DIRECTOR_OF_COMMUNICATIONS = "director of communications"
    # DIRECTOR_OF_OUTREACH = "director of outreach"
    DIRECTOR_OF_MULTIMEDIA = "director of multimedia"
    DIRECTOR_OF_ARCHIVES = "director of archives"
    EXECUTIVE_AT_LARGE = "executive at large"
    FIRST_YEAR_REPRESENTATIVE = "first year representative"

    ELECTIONS_OFFICER = "election officer"
    SFSS_COUNCIL_REPRESENTATIVE = "sfss council representative"
    FROSH_WEEK_CHAIR = "frosh week chair"

    SYSTEM_ADMINISTRATOR = "system administrator"
    WEBMASTER = "webmaster"
    SOCIAL_MEDIA_MANAGER = "social media manager"


class OfficerPosition:
    @staticmethod
    def position_list() -> list[OfficerPositionEnum]:
        return _OFFICER_POSITION_LIST

    @staticmethod
    def length_in_semesters(position: OfficerPositionEnum) -> int | None:
        # TODO (#101): ask the committee to maintain a json file with all the important details from the constitution
        """How many semester position is active for, according to the CSSS Constitution"""
        if position not in _LENGTH_MAP:
            # this can occur for legacy positions
            return None
        else:
            return _LENGTH_MAP[position]

    @staticmethod
    def to_email(position: OfficerPositionEnum) -> str | None:
        return _EMAIL_MAP.get(position, None)

    @staticmethod
    def num_active(position: str) -> int | None:
        """
        The number of executive positions active at a given time
        """
        # None means there can be any number active
        if (
            position == OfficerPositionEnum.EXECUTIVE_AT_LARGE
            or position == OfficerPositionEnum.FIRST_YEAR_REPRESENTATIVE
        ):
            return 2
        elif position == OfficerPositionEnum.FROSH_WEEK_CHAIR or position == OfficerPositionEnum.SOCIAL_MEDIA_MANAGER:
            return None
        else:
            return 1

    @staticmethod
    def is_signer(position: str) -> bool:
        """
        If the officer is a signing authority of the CSSS
        """
        return (
            position == OfficerPositionEnum.PRESIDENT
            or position == OfficerPositionEnum.VICE_PRESIDENT
            or position == OfficerPositionEnum.TREASURER
            or position == OfficerPositionEnum.DIRECTOR_OF_RESOURCES
            or position == OfficerPositionEnum.DIRECTOR_OF_EVENTS
        )

    @staticmethod
    def expected_positions() -> list[str]:
        # TODO (#93): use this function in the daily cronjobs
        return [
            OfficerPositionEnum.PRESIDENT,
            OfficerPositionEnum.VICE_PRESIDENT,
            OfficerPositionEnum.TREASURER,
            OfficerPositionEnum.DIRECTOR_OF_RESOURCES,
            OfficerPositionEnum.DIRECTOR_OF_EVENTS,
            OfficerPositionEnum.DIRECTOR_OF_EDUCATIONAL_EVENTS,
            OfficerPositionEnum.ASSISTANT_DIRECTOR_OF_EVENTS,
            OfficerPositionEnum.DIRECTOR_OF_COMMUNICATIONS,
            # OfficerPositionEnum.DIRECTOR_OF_OUTREACH, # TODO (#101): when https://github.com/CSSS/documents/pull/9/files merged
            OfficerPositionEnum.DIRECTOR_OF_MULTIMEDIA,
            OfficerPositionEnum.DIRECTOR_OF_ARCHIVES,
            OfficerPositionEnum.EXECUTIVE_AT_LARGE,
            # TODO (#101): expect these only during fall & spring semesters.
            # OfficerPositionEnum.FIRST_YEAR_REPRESENTATIVE,
            # ElectionsOfficer,
            OfficerPositionEnum.SFSS_COUNCIL_REPRESENTATIVE,
            OfficerPositionEnum.FROSH_WEEK_CHAIR,
            OfficerPositionEnum.SYSTEM_ADMINISTRATOR,
            OfficerPositionEnum.WEBMASTER,
        ]


_EMAIL_MAP = {
    OfficerPositionEnum.PRESIDENT: "csss-president-current@sfu.ca",
    OfficerPositionEnum.VICE_PRESIDENT: "csss-vp-current@sfu.ca",
    OfficerPositionEnum.TREASURER: "csss-treasurer-current@sfu.ca",
    OfficerPositionEnum.DIRECTOR_OF_RESOURCES: "csss-dor-current@sfu.ca",
    OfficerPositionEnum.DIRECTOR_OF_EVENTS: "csss-doe-current@sfu.ca",
    OfficerPositionEnum.DIRECTOR_OF_EDUCATIONAL_EVENTS: "csss-doee-current@sfu.ca",
    OfficerPositionEnum.ASSISTANT_DIRECTOR_OF_EVENTS: "csss-adoe-current@sfu.ca",
    OfficerPositionEnum.DIRECTOR_OF_COMMUNICATIONS: "csss-doc-current@sfu.ca",
    # OfficerPositionEnum.DIRECTOR_OF_OUTREACH,
    OfficerPositionEnum.DIRECTOR_OF_MULTIMEDIA: "csss-domm-current@sfu.ca",
    OfficerPositionEnum.DIRECTOR_OF_ARCHIVES: "csss-doa-current@sfu.ca",
    OfficerPositionEnum.EXECUTIVE_AT_LARGE: "csss-eal-current@sfu.ca",
    OfficerPositionEnum.FIRST_YEAR_REPRESENTATIVE: "csss-fyr-current@sfu.ca",
    OfficerPositionEnum.ELECTIONS_OFFICER: "csss-election@sfu.ca",
    OfficerPositionEnum.SFSS_COUNCIL_REPRESENTATIVE: "csss-councilrep@sfu.ca",
    OfficerPositionEnum.FROSH_WEEK_CHAIR: "csss-froshchair@sfu.ca",
    OfficerPositionEnum.SYSTEM_ADMINISTRATOR: "csss-sysadmin@sfu.ca",
    OfficerPositionEnum.WEBMASTER: "csss-webmaster@sfu.ca",
    OfficerPositionEnum.SOCIAL_MEDIA_MANAGER: "N/A",
}

# None, means that the length of the position does not have a set length in semesters
_LENGTH_MAP = {
    OfficerPositionEnum.PRESIDENT: 3,
    OfficerPositionEnum.VICE_PRESIDENT: 3,
    OfficerPositionEnum.TREASURER: 3,
    OfficerPositionEnum.DIRECTOR_OF_RESOURCES: 3,
    OfficerPositionEnum.DIRECTOR_OF_EVENTS: 3,
    OfficerPositionEnum.DIRECTOR_OF_EDUCATIONAL_EVENTS: 3,
    OfficerPositionEnum.ASSISTANT_DIRECTOR_OF_EVENTS: 3,
    OfficerPositionEnum.DIRECTOR_OF_COMMUNICATIONS: 3,
    # OfficerPositionEnum.DIRECTOR_OF_OUTREACH: 3,
    OfficerPositionEnum.DIRECTOR_OF_MULTIMEDIA: 3,
    OfficerPositionEnum.DIRECTOR_OF_ARCHIVES: 3,
    OfficerPositionEnum.EXECUTIVE_AT_LARGE: 1,
    OfficerPositionEnum.FIRST_YEAR_REPRESENTATIVE: 2,
    OfficerPositionEnum.ELECTIONS_OFFICER: None,
    OfficerPositionEnum.SFSS_COUNCIL_REPRESENTATIVE: 3,
    OfficerPositionEnum.FROSH_WEEK_CHAIR: None,
    OfficerPositionEnum.SYSTEM_ADMINISTRATOR: None,
    OfficerPositionEnum.WEBMASTER: None,
    OfficerPositionEnum.SOCIAL_MEDIA_MANAGER: None,
}

_OFFICER_POSITION_LIST = [
    OfficerPositionEnum.PRESIDENT,
    OfficerPositionEnum.VICE_PRESIDENT,
    OfficerPositionEnum.TREASURER,
    OfficerPositionEnum.DIRECTOR_OF_RESOURCES,
    OfficerPositionEnum.DIRECTOR_OF_EVENTS,
    OfficerPositionEnum.DIRECTOR_OF_EDUCATIONAL_EVENTS,
    OfficerPositionEnum.ASSISTANT_DIRECTOR_OF_EVENTS,
    OfficerPositionEnum.DIRECTOR_OF_COMMUNICATIONS,
    # OfficerPositionEnum.DIRECTOR_OF_OUTREACH,
    OfficerPositionEnum.DIRECTOR_OF_MULTIMEDIA,
    OfficerPositionEnum.DIRECTOR_OF_ARCHIVES,
    OfficerPositionEnum.EXECUTIVE_AT_LARGE,
    OfficerPositionEnum.FIRST_YEAR_REPRESENTATIVE,
    OfficerPositionEnum.ELECTIONS_OFFICER,
    OfficerPositionEnum.SFSS_COUNCIL_REPRESENTATIVE,
    OfficerPositionEnum.FROSH_WEEK_CHAIR,
    OfficerPositionEnum.SYSTEM_ADMINISTRATOR,
    OfficerPositionEnum.WEBMASTER,
    OfficerPositionEnum.SOCIAL_MEDIA_MANAGER,
]

GENERAL_ELECTION_POSITIONS = [
    OfficerPositionEnum.PRESIDENT,
    OfficerPositionEnum.VICE_PRESIDENT,
    OfficerPositionEnum.TREASURER,
    OfficerPositionEnum.DIRECTOR_OF_RESOURCES,
    OfficerPositionEnum.DIRECTOR_OF_EVENTS,
    OfficerPositionEnum.DIRECTOR_OF_EDUCATIONAL_EVENTS,
    OfficerPositionEnum.ASSISTANT_DIRECTOR_OF_EVENTS,
    OfficerPositionEnum.DIRECTOR_OF_COMMUNICATIONS,
    # OfficerPositionEnum.DIRECTOR_OF_OUTREACH,
    OfficerPositionEnum.DIRECTOR_OF_MULTIMEDIA,
    OfficerPositionEnum.DIRECTOR_OF_ARCHIVES,
]

COUNCIL_REP_ELECTION_POSITIONS = [
    OfficerPositionEnum.SFSS_COUNCIL_REPRESENTATIVE,
]
