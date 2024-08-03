from constants import guild_id, github_org_name
from dataclasses import dataclass
from json import dumps
import os
import requests
from requests import Response
from typing import Any

@dataclass
class GithubUser:
    username: str
    id: int
    name: str

async def _github_request_get(
        url: str,
        token: str
) -> Response:
    result = requests.get(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2022-11-28"
        }
    )
    return result

async def _github_request_post(
        url: str,
        token: str,
        post_data: Any
) -> Response:
    result = requests.post(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2022-11-28"
        },
        data=post_data
    )
    return result

async def get_user_by_username(
        username: str
) -> GithubUser:
    result = await _github_request_get(f"https://api.github.com/users/{username}",
                              os.environ.get("GITHUB_TOKEN"))
    result_json = result.json()
    return [GithubUser(user["login"], user["id"], user["name"]) for user in [result_json]]

async def get_user_by_id(
    id: str    
) -> int:
    result = await _github_request_get(f"https://api.github.com/user/{id}",
                              os.environ.get("GITHUB_TOKEN"))
    result_json = result.json()
    return [GithubUser(user["login"], user["id"], user["name"]) for user in [result_json]]
    
async def add_user_to_org(
        org: str = github_org_name,
        uid: str | None = None,
        email: str | None = None
) -> None:
    if uid == None and email == None:
        raise Exception("uid and username cannot both be empty")
    result = None
    # Arbitrarily prefer uid
    if uid is not None and email is None:
        result = await _github_request_post(f"https://api.github.com/orgs/{org}/invitations", 
                               os.environ.get("GITHUB_TOKEN"), 
                               dumps({"invitee_id":uid, "role":"direct_member"}))
    # Assume at this point both exist, but use email
    else:
        result = await _github_request_post(f"https://api.github.com/orgs/{org}/invitations", 
                               os.environ.get("GITHUB_TOKEN"), 
                               dumps({"email":email, "role":"direct_member"}))
    result_json = result.json()
    # Logging here potentially?
    if(result_json["status"] == "422"):
        raise Exception(result_json["message"] + ": " + str([error["message"] for error in result_json["errors"]]))