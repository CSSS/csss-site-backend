# TODO: does this allow importing anything from the module?

from github.internals import list_members, list_teams 
from admin.email import send_email

# Rules:
# - all past officers will be members of the github org
# - all past officers will be put in past_officers team
# - all current officers will be put in the officers team
# - 


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
    team
    for (name, kind) in GITHUB_TEAMS.items()
    if kind == "auto"
]

# TODO: move these functions to github.public.py

def current_permissions() -> dict[str, GithubUserPermissions]:
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

    return user_permissions

def set_user_teams(username: str, old_teams: list[str], new_teams: list[str]):
    for team_slug in old_teams:
        if team_slug not in new_teams:
            remove_user_from_team(term.username, team_slug)

    for team_slug in new_teams:
        if team_slug not in old_teams:
            # TODO: what happens when adding a user to a team who is not part of the github org yet?
            add_user_to_team(term.username, team_slug)

def invite_user(github_username: str):
    # invite this user to the github organization
    # TODO: is an invited user considered a member of the organization?
    pass

