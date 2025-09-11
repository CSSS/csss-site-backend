from officers.types import OfficerPositionEnum


class OfficerPosition:
    PRESIDENT = "president"
    VICE_PRESIDENT = "vice-president"
    TREASURER = "treasurer"

    DIRECTOR_OF_RESOURCES = "director of resources"
    DIRECTOR_OF_EVENTS = "director of events"
    DIRECTOR_OF_EDUCATIONAL_EVENTS = "director of educational events"
    ASSISTANT_DIRECTOR_OF_EVENTS = "assistant director of events"
    DIRECTOR_OF_COMMUNICATIONS = "director of communications"
    #DIRECTOR_OF_OUTREACH = "director of outreach"
    DIRECTOR_OF_MULTIMEDIA = "director of multimedia"
    DIRECTOR_OF_ARCHIVES = "director of archives"
    EXECUTIVE_AT_LARGE = "executive at large"
    FIRST_YEAR_REPRESENTATIVE = "first year representative"

    ELECTIONS_OFFICER = "elections officer"
    SFSS_COUNCIL_REPRESENTATIVE = "sfss council representative"
    FROSH_WEEK_CHAIR = "frosh week chair"

    SYSTEM_ADMINISTRATOR = "system administrator"
    WEBMASTER = "webmaster"
    SOCIAL_MEDIA_MANAGER = "social media manager"

    @staticmethod
    def position_list() -> list[OfficerPositionEnum]:
        return _OFFICER_POSITION_LIST

    @staticmethod
    def length_in_semesters(position: str) -> int | None:
        # TODO (#101): ask the committee to maintain a json file with all the important details from the constitution
        """How many semester position is active for, according to the CSSS Constitution"""
        if position not in _LENGTH_MAP:
            # this can occur for legacy positions
            return None
        else:
            return _LENGTH_MAP[position]

    @staticmethod
    def to_email(position: str) -> str | None:
        return _EMAIL_MAP.get(position, None)

    @staticmethod
    def num_active(position: str) -> int | None:
        """
        The number of executive positions active at a given time
        """
        # None means there can be any number active
        if (
            position == OfficerPosition.EXECUTIVE_AT_LARGE
            or position == OfficerPosition.FIRST_YEAR_REPRESENTATIVE
        ):
            return 2
        elif (
            position == OfficerPosition.FROSH_WEEK_CHAIR
            or position == OfficerPosition.SOCIAL_MEDIA_MANAGER
        ):
            return None
        else:
            return 1

    @staticmethod
    def is_signer(position: str) -> bool:
        """
        If the officer is a signing authority of the CSSS
        """
        return (
            position == OfficerPosition.PRESIDENT
            or position == OfficerPosition.VICE_PRESIDENT
            or position == OfficerPosition.TREASURER
            or position == OfficerPosition.DIRECTOR_OF_RESOURCES
            or position == OfficerPosition.DIRECTOR_OF_EVENTS
        )

    @staticmethod
    def expected_positions() -> list[str]:
        # TODO (#93): use this function in the daily cronjobs
        return [
            OfficerPosition.PRESIDENT,
            OfficerPosition.VICE_PRESIDENT,
            OfficerPosition.TREASURER,

            OfficerPosition.DIRECTOR_OF_RESOURCES,
            OfficerPosition.DIRECTOR_OF_EVENTS,
            OfficerPosition.DIRECTOR_OF_EDUCATIONAL_EVENTS,
            OfficerPosition.ASSISTANT_DIRECTOR_OF_EVENTS,
            OfficerPosition.DIRECTOR_OF_COMMUNICATIONS,
            #OfficerPosition.DIRECTOR_OF_OUTREACH, # TODO (#101): when https://github.com/CSSS/documents/pull/9/files merged
            OfficerPosition.DIRECTOR_OF_MULTIMEDIA,
            OfficerPosition.DIRECTOR_OF_ARCHIVES,
            OfficerPosition.EXECUTIVE_AT_LARGE,
            # TODO (#101): expect these only during fall & spring semesters.
            #OfficerPosition.FIRST_YEAR_REPRESENTATIVE,

            #ElectionsOfficer,
            OfficerPosition.SFSS_COUNCIL_REPRESENTATIVE,
            OfficerPosition.FROSH_WEEK_CHAIR,

            OfficerPosition.SYSTEM_ADMINISTRATOR,
            OfficerPosition.WEBMASTER,
        ]

_EMAIL_MAP = {
    OfficerPosition.PRESIDENT: "csss-president-current@sfu.ca",
    OfficerPosition.VICE_PRESIDENT: "csss-vp-current@sfu.ca",
    OfficerPosition.TREASURER: "csss-treasurer-current@sfu.ca",

    OfficerPosition.DIRECTOR_OF_RESOURCES: "csss-dor-current@sfu.ca",
    OfficerPosition.DIRECTOR_OF_EVENTS: "csss-doe-current@sfu.ca",
    OfficerPosition.DIRECTOR_OF_EDUCATIONAL_EVENTS: "csss-doee-current@sfu.ca",
    OfficerPosition.ASSISTANT_DIRECTOR_OF_EVENTS: "csss-adoe-current@sfu.ca",
    OfficerPosition.DIRECTOR_OF_COMMUNICATIONS: "csss-doc-current@sfu.ca",
    #OfficerPosition.DIRECTOR_OF_OUTREACH,
    OfficerPosition.DIRECTOR_OF_MULTIMEDIA: "csss-domm-current@sfu.ca",
    OfficerPosition.DIRECTOR_OF_ARCHIVES: "csss-doa-current@sfu.ca",
    OfficerPosition.EXECUTIVE_AT_LARGE: "csss-eal-current@sfu.ca",
    OfficerPosition.FIRST_YEAR_REPRESENTATIVE: "csss-fyr-current@sfu.ca",

    OfficerPosition.ELECTIONS_OFFICER: "csss-elections@sfu.ca",
    OfficerPosition.SFSS_COUNCIL_REPRESENTATIVE: "csss-councilrep@sfu.ca",
    OfficerPosition.FROSH_WEEK_CHAIR: "csss-froshchair@sfu.ca",

    OfficerPosition.SYSTEM_ADMINISTRATOR: "csss-sysadmin@sfu.ca",
    OfficerPosition.WEBMASTER: "csss-webmaster@sfu.ca",
    OfficerPosition.SOCIAL_MEDIA_MANAGER: "N/A",
}

# None, means that the length of the position does not have a set length in semesters
_LENGTH_MAP = {
    OfficerPosition.PRESIDENT: 3,
    OfficerPosition.VICE_PRESIDENT: 3,
    OfficerPosition.TREASURER: 3,

    OfficerPosition.DIRECTOR_OF_RESOURCES: 3,
    OfficerPosition.DIRECTOR_OF_EVENTS: 3,
    OfficerPosition.DIRECTOR_OF_EDUCATIONAL_EVENTS: 3,
    OfficerPosition.ASSISTANT_DIRECTOR_OF_EVENTS: 3,
    OfficerPosition.DIRECTOR_OF_COMMUNICATIONS: 3,
    #OfficerPosition.DIRECTOR_OF_OUTREACH: 3,
    OfficerPosition.DIRECTOR_OF_MULTIMEDIA: 3,
    OfficerPosition.DIRECTOR_OF_ARCHIVES: 3,
    OfficerPosition.EXECUTIVE_AT_LARGE: 1,
    OfficerPosition.FIRST_YEAR_REPRESENTATIVE: 2,

    OfficerPosition.ELECTIONS_OFFICER: None,
    OfficerPosition.SFSS_COUNCIL_REPRESENTATIVE: 3,
    OfficerPosition.FROSH_WEEK_CHAIR: None,

    OfficerPosition.SYSTEM_ADMINISTRATOR: None,
    OfficerPosition.WEBMASTER: None,
    OfficerPosition.SOCIAL_MEDIA_MANAGER: None,
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
    #OfficerPositionEnum.DIRECTOR_OF_OUTREACH,
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
    #OfficerPositionEnum.DIRECTOR_OF_OUTREACH,
    OfficerPositionEnum.DIRECTOR_OF_MULTIMEDIA,
    OfficerPositionEnum.DIRECTOR_OF_ARCHIVES,
]

COUNCIL_REP_ELECTION_POSITIONS = [
    OfficerPositionEnum.SFSS_COUNCIL_REPRESENTATIVE,
]
