import logging
from enum import Enum
from typing import Self

_logger = logging.getLogger(__name__)

# TODO: remove enum, b/d python enums suck
class OfficerPosition(Enum):
    President = "president"
    VicePresident = "vice-president"
    Treasurer = "treasurer"

    DirectorOfResources = "director of resources"
    DirectorOfEvents = "director of events"
    DirectorOfEducationalEvents = "director of educational events"
    AssistantDirectorOfEvents = "assistant director of events"
    DirectorOfCommunications = "director of communications"
    #DirectorOfOutreach = "director of outreach"
    DirectorOfMultimedia = "director of multimedia"
    DirectorOfArchives = "director of archives"
    ExecutiveAtLarge = "executive at large"
    FirstYearRepresentative = "first year representative"

    ElectionsOfficer = "elections officer"
    SFSSCouncilRepresentative = "sfss council representative"
    FroshWeekChair = "frosh week chair"

    SystemAdministrator = "system administrator"
    Webmaster = "webmaster"
    SocialMediaManager = "social media manager"

    @staticmethod
    def from_string(position: str) -> Self | None:
        for item in OfficerPosition:
            if position == item.value:
                return item

        _logger.warning(f"Unknown OfficerPosition position = {position}. reporting N/A.")
        return None

    def to_string(self) -> str:
        return self.value

    def to_email(self) -> str:
        match self:
            case OfficerPosition.President:
                return "csss-president-current@sfu.ca"
            case OfficerPosition.VicePresident:
                return "csss-vp-current@sfu.ca"
            case OfficerPosition.Treasurer:
                return "csss-treasurer-current@sfu.ca"

            case OfficerPosition.DirectorOfResources:
                return "csss-dor-current@sfu.ca"
            case OfficerPosition.DirectorOfEvents:
                return "csss-doe-current@sfu.ca"
            case OfficerPosition.DirectorOfEducationalEvents:
                return "csss-doee-current@sfu.ca"
            case OfficerPosition.AssistantDirectorOfEvents:
                return "csss-adoe-current@sfu.ca"
            case OfficerPosition.DirectorOfCommunications:
                return "csss-doc-current@sfu.ca"
            case OfficerPosition.DirectorOfMultimedia:
                return "csss-domm-current@sfu.ca"
            case OfficerPosition.DirectorOfArchives:
                return "csss-doa-current@sfu.ca"
            case OfficerPosition.ExecutiveAtLarge:
                return "csss-eal-current@sfu.ca"
            case OfficerPosition.FirstYearRepresentative:
                return "csss-fyr-current@sfu.ca"

            case OfficerPosition.ElectionsOfficer:
                return "csss-elections@sfu.ca"
            case OfficerPosition.SFSSCouncilRepresentative:
                return "csss-councilrep@sfu.ca"
            case OfficerPosition.FroshWeekChair:
                return "csss-froshchair@sfu.ca"

            case OfficerPosition.SystemAdministrator:
                return "csss-sysadmin@sfu.ca"
            case OfficerPosition.Webmaster:
                return "csss-webmaster@sfu.ca"
            case OfficerPosition.SocialMediaManager:
                return "N/A"

    def num_active(self) -> int | None:
        """
        The number of executive positions active at a given time
        """
        # None means there can be any number active
        if (
            self == OfficerPosition.ExecutiveAtLarge
            or self == OfficerPosition.FirstYearRepresentative
        ):
            return 2
        elif (
            self == OfficerPosition.FroshWeekChair
            or self == OfficerPosition.SocialMediaManager
        ):
            # TODO: configure this value in a database table somewhere?
            return None
        else:
            return 1

    def is_signer(self) -> bool:
        """
        If the officer is a signing authority of the CSSS
        """
        return (
            self == OfficerPosition.President
            or self == OfficerPosition.VicePresident
            or self == OfficerPosition.Treasurer
            or self == OfficerPosition.DirectorOfResources
            or self == OfficerPosition.DirectorOfEvents
        )

    @staticmethod
    def expected_positions() -> list[Self]:
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
