# TODO: does this allow importing anything from the module?

from github.internals import 
from admin.email import send_email

# TODO: move this to github.constants.py
GITHUB_TEAMS = {
    "doa" : "auto",
    "election_officer": "auto",
    "officers": "auto",
    "w3_committee": "manual",
    "wall_e": "manual",
}

# TODO: move these functions to github.public.py

def current_permissions() -> list[GithubUserPermissions]:
    person_list = []

    # this function should return a list of members that have permisisons
    
    # get info for each person in an auto github team

    # log warning if there are any unknown teams

    # log error & email if there are any missing teams
    # send_email("csss-sysadmin@sfu.ca", "ERROR: Missing Team", "...") 
    pass

def invite_user(github_username: str):
    # invite this user to the github organization
    pass


