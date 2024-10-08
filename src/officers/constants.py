import logging
from enum import Enum
from typing import Self

_logger = logging.getLogger(__name__)

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
    def position_list() -> list[str]:
        return _OFFICER_POSITION_LIST

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
            position == OfficerPosition.ExecutiveAtLarge
            or position == OfficerPosition.FirstYearRepresentative
        ):
            return 2
        elif (
            position == OfficerPosition.FroshWeekChair
            or position == OfficerPosition.SocialMediaManager
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
            position == OfficerPosition.President
            or position == OfficerPosition.VicePresident
            or position == OfficerPosition.Treasurer
            or position == OfficerPosition.DirectorOfResources
            or position == OfficerPosition.DirectorOfEvents
        )

    @staticmethod
    def expected_positions() -> list[str]:
        return [
            OfficerPosition.President,
            OfficerPosition.VicePresident,
            OfficerPosition.Treasurer,

            OfficerPosition.DirectorOfResources,
            OfficerPosition.DirectorOfEvents,
            OfficerPosition.DirectorOfEducationalEvents,
            OfficerPosition.AssistantDirectorOfEvents,
            OfficerPosition.DirectorOfCommunications,
            #DirectorOfOutreach, # TODO: when https://github.com/CSSS/documents/pull/9/files merged
            OfficerPosition.DirectorOfMultimedia,
            OfficerPosition.DirectorOfArchives,
            OfficerPosition.ExecutiveAtLarge,
            # TODO: expect these only during fall & spring semesters. Also, TODO: this todo is correct...
            #FirstYearRepresentative,

            #ElectionsOfficer,
            OfficerPosition.SFSSCouncilRepresentative,
            OfficerPosition.FroshWeekChair,

            OfficerPosition.SystemAdministrator,
            OfficerPosition.Webmaster,
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

_OFFICER_POSITION_LIST = [
    OfficerPosition.PRESIDENT,
    OfficerPosition.VICE_PRESIDENT,
    OfficerPosition.TREASURER,

    OfficerPosition.DIRECTOR_OF_RESOURCES,
    OfficerPosition.DIRECTOR_OF_EVENTS,
    OfficerPosition.DIRECTOR_OF_EDUCATIONAL_EVENTS,
    OfficerPosition.ASSISTANT_DIRECTOR_OF_EVENTS,
    OfficerPosition.DIRECTOR_OF_COMMUNICATIONS,
    #OfficerPosition.DIRECTOR_OF_OUTREACH,
    OfficerPosition.DIRECTOR_OF_MULTIMEDIA,
    OfficerPosition.DIRECTOR_OF_ARCHIVES,
    OfficerPosition.EXECUTIVE_AT_LARGE,
    OfficerPosition.FIRST_YEAR_REPRESENTATIVE,

    OfficerPosition.ELECTIONS_OFFICER,
    OfficerPosition.SFSS_COUNCIL_REPRESENTATIVE,
    OfficerPosition.FROSH_WEEK_CHAIR,

    OfficerPosition.SYSTEM_ADMINISTRATOR,
    OfficerPosition.WEBMASTER,
    OfficerPosition.SOCIAL_MEDIA_MANAGER,
]
