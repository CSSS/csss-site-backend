import os
from dataclasses import dataclass
from json import dumps
from typing import Any

import requests
from constants import github_org_name
from requests import Response


@dataclass
class GithubUser:
    username: str
    id: int
    name: str

@dataclass
class GithubTeam:
    id: int
    url: str
    name: str
    # slugs are the space-free special names that github likes to use
    slug: str

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
        os.environ.get("GITHUB_TOKEN"),
    )
    result_json = result.json()
    if result_json["status"] == "404":
        return None
    else:
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
        os.environ.get("GITHUB_TOKEN"),
    )
    result_json = result.json()
    if result_json["status"] == "404":
        return None
    else:
        return GithubUser(result_json["login"], result_json["id"], result_json["name"])

async def add_user_to_org(
    org: str = github_org_name,
    uid: str | None = None,
    email: str | None = None
) -> None:
    """
        Takes one of either uid or email. Fails if provided both.
    """
    result = None
    if uid is None and email is None:
        raise ValueError("uid and username cannot both be empty")
    elif uid is not None and email is not None:
        raise ValueError("cannot populate both uid and email")
    # Arbitrarily prefer uid
    elif uid is not None:
        result = await _github_request_post(
            f"https://api.github.com/orgs/{org}/invitations",
            os.environ.get("GITHUB_TOKEN"),
            dumps({"invitee_id":uid, "role":"direct_member"})
        )
    elif email is not None:
        result = await _github_request_post(
            f"https://api.github.com/orgs/{org}/invitations",
            os.environ.get("GITHUB_TOKEN"),
            dumps({"email":email, "role":"direct_member"})
        )

    # Logging here potentially?
    if result.status_code != 201:
        result_json = result.json()
        raise Exception(
            f"Status code {result.status_code} returned when attempting to add user to org: "
            f"{result_json['message']}: {[error['message'] for error in result_json['errors']]}"
        )

async def delete_user_from_org(
    username: str,
    org: str = github_org_name
) -> None:
    if username is None:
        raise Exception("Username cannot be empty")
    result = await _github_request_delete(
        f"https://api.github.com/orgs/{org}/memberships/{username}",
        os.environ.get("GITHUB_TOKEN")
    )

    # Logging here potentially?
    if result.status_code != 204:
        raise Exception(f"Status code {result.status_code} returned when attempting to delete user {username} from organization {org}")

async def get_teams(
    org: str = github_org_name
) -> list[str]:
    result = await _github_request_get(f"https://api.github.com/orgs/{org}/teams", os.environ.get("GITHUB_TOKEN"))
    json_result = result.json()
    return [GithubTeam(team["id"], team["url"], team["name"], team["slug"]) for team in json_result]

async def add_user_to_team(
    username: str,
    slug: str,
    org: str = github_org_name
) -> None:
    result = await _github_request_put(
        f"https://api.github.com/orgs/{org}/teams/{slug}/memberships/{username}",
        os.environ.get("GITHUB_TOKEN"),
        dumps({"role":"member"}),
    )

    # Logging here potentially?
    if result.status_code != 200:
        result_json = result.json()
        raise Exception(f"Status code {result.status_code} returned when attempting to add user to team: {result_json['message']}")

async def remove_user_from_team(
    username: str,
    slug: str,
    org: str = github_org_name
) -> None:
    result = await _github_request_delete(
        f"https://api.github.com/orgs/{org}/teams/{slug}/memberships/{username}",
        os.environ.get("GITHUB_TOKEN"),
    )
    if result.status_code != 204:
        raise Exception(f"Status code {result.status_code} returned when attempting to delete user {username} from team {slug}")

