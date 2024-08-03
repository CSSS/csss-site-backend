from dataclasses import dataclass
from typing import Any

import requests
from constants import guild_id
from requests import Response

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