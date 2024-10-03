import os
from json import dumps
from typing import Any

import requests
from constants import GITHUB_ORG_NAME
from requests import Response

from github.types import GithubTeam, GithubUser

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")

# TODO: go through this module & make sure that all functions check for response.status_code
# being invalid as specified by the API endpoints

async def _github_request_get(
    url: str,
    token: str
) -> Response | None:
    result = requests.get(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2022-11-28"
        }
    )
    rate_limit_remaining = int(result.headers["x-ratelimit-remaining"])
    if rate_limit_remaining < 50:
        # Less than 50 api calls remaining before being rate limited
        return None

    return result

async def _github_request_post(
    url: str,
    token: str,
    post_data: Any
) -> Response | None:
    result = requests.post(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2022-11-28"
        },
        data=post_data
    )
    rate_limit_remaining = int(result.headers["x-ratelimit-remaining"])
    if rate_limit_remaining < 50:
        # Less than 50 api calls remaining before being rate limited, please try again later
        return None

    return result

async def _github_request_delete(
    url: str,
    token: str
) -> Response | None:
    result = requests.delete(
        url,
        headers = {
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2022-11-28"
        }
    )
    rate_limit_remaining = int(result.headers["x-ratelimit-remaining"])
    if rate_limit_remaining < 50:
        # Less than 50 api calls remaining before being rate limited
        return None

    return result

async def _github_request_put(
    url: str,
    token: str,
    put_data: Any
) -> Response | None:
    result = requests.put(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2022-11-28"},
        data=put_data
    )
    rate_limit_remaining = int(result.headers["x-ratelimit-remaining"])
    if rate_limit_remaining < 50:
        # Less than 50 api calls remaining before being rate limited
        return None

    return result

async def get_user_by_username(
    username: str
) -> GithubUser | None:
    """
        Takes in a Github username and returns an instance of GithubUser.

        Returns None if no such user was found.
    """
    result = await _github_request_get(
        f"https://api.github.com/users/{username}",
        GITHUB_TOKEN,
    )
    if result.status_code == 404:
        return None

    result_json = result.json()
    return GithubUser(result_json["login"], result_json["id"], result_json["name"])

async def get_user_by_id(
    uid: str
) -> GithubUser | None:
    """
        Takes in a Github user id and returns an instance of GithubUser.

        Returns None if no such user was found.
    """
    result = await _github_request_get(
        f"https://api.github.com/user/{uid}",
        GITHUB_TOKEN,
    )
    if result.status == 404:
        return None

    result_json = result.json()
    return GithubUser(result_json["login"], result_json["id"], result_json["name"])

# TODO: if needed, add support for getting user by email

# TODO: can we revoke access before an invite is accepeted?
async def invite_user(
    uid: str,
    team_id_list: list[str] | None = None,
    org: str = GITHUB_ORG_NAME,
) -> None:
    """Invites the user & gives them access to the supplied teams"""
    # TODO: how long until the invite goes out of date?
    if team_id_list is None:
        team_id_list = []

    result = await _github_request_post(
        f"https://api.github.com/orgs/{org}/invitations",
        GITHUB_TOKEN,
        dumps({"invitee_id":uid, "role":"direct_member", "team_ids":team_id_list})
    )

    # Logging here potentially?
    if result.status_code != 201:
        result_json = result.json()
        raise Exception(
            f"Status code {result.status_code} returned when attempting to invite user: "
            f"{result_json['message']}: {[error['message'] for error in result_json['errors']]}"
        )

async def delete_user_from_org(
    username: str | None,
    org: str = GITHUB_ORG_NAME
) -> None:
    if username is None:
        raise ValueError("Username cannot be empty")

    result = await _github_request_delete(
        f"https://api.github.com/orgs/{org}/memberships/{username}", GITHUB_TOKEN
    )

    # Logging here potentially?
    if result.status_code != 204:
        raise Exception(f"Status code {result.status_code} returned when attempting to delete user {username} from organization {org}")

async def list_teams(
    org: str = GITHUB_ORG_NAME
) -> list[str]:
    result = await _github_request_get(f"https://api.github.com/orgs/{org}/teams", GITHUB_TOKEN)
    return [
        GithubTeam(team["id"], team["url"], team["name"], team["slug"])
        for team in result.json()
    ]

async def list_team_members(
    team_slug: str,
    org: str = GITHUB_ORG_NAME
):
    result = await _github_request_get(
        f"https://api.github.com/orgs/{org}/teams/{team_slug}/members",
        GITHUB_TOKEN
    )
    return [
        GithubUser(user["login"], user["id"], user["name"])
        for user in result.json()
    ]

async def add_user_to_team(
    username: str,
    team_slug: str,
    org: str = GITHUB_ORG_NAME
) -> None:
    result = await _github_request_put(
        f"https://api.github.com/orgs/{org}/teams/{team_slug}/memberships/{username}",
        GITHUB_TOKEN,
        dumps({"role":"member"}),
    )

    # Logging here potentially?
    if result.status_code != 200:
        result_json = result.json()
        raise Exception(f"Status code {result.status_code} returned when attempting to add user to team: {result_json['message']}")

async def remove_user_from_team(
    username: str,
    team_slug: str,
    org: str = GITHUB_ORG_NAME
) -> None:
    result = await _github_request_delete(
        f"https://api.github.com/orgs/{org}/teams/{team_slug}/memberships/{username}",
        GITHUB_TOKEN,
    )
    if result.status_code != 204:
        raise Exception(f"Status code {result.status_code} returned when attempting to delete user {username} from team {team_slug}")

async def list_members(
    org: str = GITHUB_ORG_NAME,
    page_number: int = 1,
    page_size: int = 99,
) -> list[GithubUser]:
    result = await _github_request_get(
        f"https://api.github.com/orgs/{org}/members?per_page={page_size}&page={page_number}",
        GITHUB_TOKEN
    )

    if result.status_code != 200:
        raise Exception(f"Got result with status_code={result.status_code}, and contents={result.text}")

    return [
        (user["login"], user["id"])
        for user in result.json()
    ]
