# TODO: does this allow importing anything from the module?
import logging
import os

from github.internals import add_user_to_team, list_members, list_team_members, list_teams, remove_user_from_team
from github.types import GithubUserPermissions

#from admin.email import send_email
from officers.constants import OfficerPosition

# Rules:
# - all past officers will be members of the github org
# - all past officers will be put in past_officers team
# - all current officers will be put in the officers team

_logger = logging.getLogger(__name__)

# TODO: move this to github.constants.py
GITHUB_TEAMS = {
    "doa": "auto",
    "election_officer": "auto",

    "officers": "auto",
    # TODO: create the past_officers team
    "past_officers": "auto",

    "w3_committee": "manual",
    "wall_e": "manual",
}
AUTO_GITHUB_TEAMS = [
    name
    for (name, kind) in GITHUB_TEAMS.items()
    if kind == "auto"
]

def is_active() -> bool:
    # if there is no github token, then consider the module inactive; calling functions may fail without warning!
    return os.environ.get("GITHUB_TOKEN") is not None

def officer_teams(position: str) -> list[str]:
    if position == OfficerPosition.DIRECTOR_OF_ARCHIVES:
        return ["doa", "officers"]
    elif position == OfficerPosition.ELECTIONS_OFFICER:
        return ["election_officer", "officers"]
    else:
        return ["officers"]

# TODO: move these functions to github.public.py

def all_permissions() -> dict[str, GithubUserPermissions]:
    """
    return a list of members in the organization (org) & their permissions
    """
    member_list = list_members()
    member_name_list = { member.name for member in member_list }

    team_list = []
    for team in list_teams():
        if team.name not in GITHUB_TEAMS.keys():
            _logger.warning(f"Found unexpected github team {team.name}")
            continue
        elif GITHUB_TEAMS[team.name] == "manual":
            continue
        team_list += [team]

    team_name_list = [team.name for team in team_list]
    for team_name in AUTO_GITHUB_TEAMS:
        if team_name not in team_name_list:
            # TODO: send email for all errors & warnings
            # send_email("csss-sysadmin@sfu.ca", "ERROR: Missing Team", "...")
            _logger.error(f"Could not find 'auto' team {team_name} in organization")

    user_permissions = {
        user.username: GithubUserPermissions(user.username, [])
        for user in member_list
    }
    for team in team_list:
        team_members = list_team_members(team.slug)
        for member in team_members:
            if member.name not in member_name_list:
                _logger.warning(f"Found unexpected team_member={member.name} in team_slug={team.slug} not in the organization")
                continue
            user_permissions[member.username].teams += [team.slug]

    # create a mapping between team name & team id, for use in creating invitations
    team_id_map = {}
    for team in team_list:
        team_id_map[team.slug] = team.id

    return user_permissions, team_id_map

def set_user_teams(username: str, old_teams: list[str], new_teams: list[str]):
    for team_slug in old_teams:
        if team_slug not in new_teams:
            remove_user_from_team(username, team_slug)

    for team_slug in new_teams:
        if team_slug not in old_teams:
            # TODO: what happens when adding a user to a team who is not part of the github org yet?
            add_user_to_team(username, team_slug)

def invite_user(github_username: str, teams: str):
    # invite this user to the github organization
    # TODO: is an invited user considered a member of the organization?
    pass

