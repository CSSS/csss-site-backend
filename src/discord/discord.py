import os
from dataclasses import dataclass
from time import sleep

import requests
from constants import guild_id
from requests import Response

# ----------------------- #
# api

DISCORD_CATEGORY_ID = 4
ADMINISTRATOR = 0b1000
VIEW_CHANNEL = 0b0010_0000_0000

@dataclass
class User:
    id: str
    username: str
    # Discriminators are what used to be the #xxxx after a discord username. Accounts which haven't
    # migrated over yet have them still.
    discriminator: str
    global_name: str | None = None
    avatar: str | None = None

@dataclass
class GuildMember:
    user: User
    roles: list[str] | None = None

@dataclass
class Channel:
    id: str
    type: str
    guild_id: str
    name: str
    permission_overwrites: list[str] | None = None

async def _discord_request(
    url: str,
    token: str
) -> Response:
    result = requests.get(
        url,
        headers={
            "Authorization": f"Bot {token}",
            "Content-Type": "application/json",
            "User-Agent" : "DiscordBot (https://github.com/CSSS/csss-site-backend, 1.0)"
        }
    )
    rate_limit_reset = float(result.headers["x-ratelimit-reset-after"])
    rate_limit_remaining_requests = int(result.headers["x-ratelimit-remaining"])

    if rate_limit_remaining_requests <= 2:
        # this rate limits the current thread from doing too many requests, however it won't
        # limit other threads.
        # TODO: in the future, we'll want to create a singleton that thread locks
        # usage of the same api key to N at a time, and waits if there are no requests remaining
        sleep(rate_limit_reset)

    return result

async def get_channel_members(
    cid: str,
    # TODO: hardcode guild_id (remove it as argument) if we ever refactor this module
    gid: str = guild_id
) -> list[GuildMember]:
    """
    Returns empty list if invalid channel id is provided.
    """
    channel = await get_channel(cid, gid)
    if channel is None:
        return []

    channel_overwrites = {
        x["id"]: {
            "type": x["type"],
            "allow": x["allow"],
            "deny": x["deny"],
        } for x in channel[0]["permission_overwrites"]
    }

    # note that there can exist only one @everyone override, break if found
    if gid in channel_overwrites:
        role_everyone_overrides = channel_overwrites[gid]
    else:
        role_everyone_overrides = None

    # NOTE: the @everyone role is exactly the guild id
    # this is by design and described in the discord role api
    role_everyone = await get_role_by_id(gid, gid)
    # the @everyone role always exists
    assert role_everyone is not None
    base_permission = role_everyone["permissions"]

    users = await get_guild_members(guild_id)
    roles = await get_all_roles(guild_id)

    users_with_access = []
    # note string conversion to int
    for user in users:
        permission = int(base_permission)
        # compute base permission
        for role in user.roles:
            permission |= int(roles[role][1])

        # check admin
        if permission & ADMINISTRATOR == ADMINISTRATOR:
            users_with_access.append(user)

        # check @everyone perms
        if role_everyone_overrides is not None:
            permission &= ~int(role_everyone_overrides["deny"])
            permission |= int(role_everyone_overrides["allow"])

        allow = 0
        deny = 0
        for role in user.roles:
            if role in channel_overwrites:
                allow |= int(channel_overwrites[role]["allow"])
                deny |= int(channel_overwrites[role]["deny"])
        permission &= ~deny
        permission |= allow

        # check member specific perms
        if user.user.id in channel_overwrites:
            # switching of 'deny' and 'allow' intentional
            permission &= ~int(channel_overwrites[user.user.id]["deny"])
            permission |= int(channel_overwrites[user.user.id]["allow"])

        if permission & VIEW_CHANNEL == VIEW_CHANNEL:
            if user not in users_with_access:
                users_with_access.append(user)

    return users_with_access

async def get_channel(
    cid: str,
    gid: str = guild_id
) -> Channel | None:
    token = os.environ.get("TOKEN")
    url = f"https://discord.com/api/v10/guilds/{gid}/channels"
    result = await _discord_request(url, token)

    result_json = result.json()
    channel = next((channel for channel in result_json if channel["id"] == cid), None)
    if channel is None:
        return None
    else:
        return Channel(channel["id"], channel["type"], channel["guild_id"], channel["name"], channel["permission_overwrites"])

async def get_all_channels(
    gid: str = guild_id
) -> list[str]:
    token = os.environ.get("TOKEN")
    url = f"https://discord.com/api/v10/guilds/{gid}/channels"
    result = await _discord_request(url, token)

    result_json = result.json()
    channels = [channel for channel in result_json if channel["type"] != DISCORD_CATEGORY_ID]
    channel_names = [channel["name"] for channel in channels]

    return channel_names


async def get_role_name_by_id(
    rid: str,
    gid: str = guild_id
) -> str:
    roles = await get_all_roles(gid)
    return roles[rid][0]

async def get_role_by_id(
    rid: str,
    gid: str = guild_id
) -> dict | None:
    token = os.environ.get("TOKEN")
    url = f"https://discord.com/api/v10/guilds/{gid}/roles"
    result = await _discord_request(url, token)

    result_json = result.json()
    return next((role for role in result_json if role["id"] == rid), None)

async def get_user_roles(
    uid: str,
    gid: str = guild_id
) -> list[str]:
    token = os.environ.get("TOKEN")
    url = f"https://discord.com/api/v10/guilds/{gid}/members/{uid}"
    result = await _discord_request(url, token)

    result_json = result.json()
    return result_json["roles"]


async def get_all_roles(
    gid: str = guild_id
) ->  dict[str, list[str]]:
    """
    Grabs all roles in a given guild.
    """
    token = os.environ.get("TOKEN")
    url = f"https://discord.com/api/v10/guilds/{gid}/roles"
    result = await _discord_request(url, token)

    result_json = result.json()
    roles = [([role["id"], [role["name"], role["permissions"]]]) for role in result_json]
    return dict(roles)

async def get_guild_members_with_role(
    rid: str,
    gid: str = guild_id
) -> list[GuildMember]:
    token = os.environ.get("TOKEN")
    # base case
    url = f"https://discord.com/api/v10/guilds/{gid}/members?limit=1000"
    result = await _discord_request(url, token)

    result_json = result.json()

    matched = [
        GuildMember(User(
            user["user"]["id"],
            user["user"]["username"],
            user["user"]["discriminator"],
            user["user"]["global_name"],
            user["user"]["avatar"]
        ), user["roles"])
        for user in result_json if rid in user["roles"]
    ]

    last_uid = matched[-1].user.id

    while True:
        url = f"https://discord.com/api/v10/guilds/{gid}/members?limit=1000&after={last_uid}"
        result = await _discord_request(url, token)

        result_json = result.json()

        if len(result_json) == 0:
            return matched

        res = [GuildMember(User(user["user"]["id"], user["user"]["username"], user["user"]["discriminator"], user["user"]["global_name"], user["user"]["avatar"]), user["roles"])
                    for user in result_json if rid in user["roles"]]
        matched += res

        last_uid = res[-1].user.id

async def get_guild_members(
    gid: str = guild_id
) -> list[GuildMember]:
    token = os.environ.get("TOKEN")
    # base case
    url = f"https://discord.com/api/v10/guilds/{gid}/members?limit=1000"
    result = await _discord_request(url, token)

    result_json = result.json()
    users = [GuildMember(User(user["user"]["id"], user["user"]["username"], user["user"]["discriminator"], user["user"]["global_name"], user["user"]["avatar"]), user["roles"]) for user in result_json]
    last_uid = users[-1].user.id

    while True:
        url = f"https://discord.com/api/v10/guilds/{gid}/members?limit=1000&after={last_uid}"
        result = await _discord_request(url, token)

        result_json = result.json()

        if len(result_json) == 0:
            return users

        res = [GuildMember(User(user["user"]["id"], user["user"]["username"], user["user"]["discriminator"], user["user"]["global_name"], user["user"]["avatar"]), user["roles"]) for user in result_json]
        users += res

        last_uid = res[-1].user.id

async def get_categories(
    gid: str = guild_id
) -> list[str]:
    token = os.environ.get("TOKEN")
    url = f"https://discord.com/api/v10/guilds/{gid}/channels"
    result = await _discord_request(url, token)

    result_json = result.json()
    return [category["name"] for category in result_json if category["type"] == DISCORD_CATEGORY_ID]

async def get_channels_by_category_name(
    category_name: str,
    gid: str = guild_id
) -> list[Channel]:
    token = os.environ.get("TOKEN")
    url = f"https://discord.com/api/v10/guilds/{gid}/channels"
    result = await _discord_request(url, token)

    result_json = result.json()
    # TODO: edge case if there exist duplicate category names, see get_channels_by_category_id()
    category_id = next(
        category["id"] for category in result_json
        if category["type"] == DISCORD_CATEGORY_ID
        and category["name"] == category_name
    )
    channels = [
        Channel(
            channel["id"],
            channel["type"],
            channel["guild_id"],
            channel["name"],
            channel["permission_overwrites"]
        )
        for channel in result_json
        if channel["type"] != DISCORD_CATEGORY_ID
        and channel["parent_id"] == category_id
    ]
    return channels

async def get_channels_by_category_id(
    cid: str,
    gid: str = guild_id
) -> list[Channel]:
    token = os.environ.get("TOKEN")
    url = f"https://discord.com/api/v10/guilds/{gid}/channels"
    result = await _discord_request(url, token)

    result_json = result.json()
    channels = [
        Channel(
            channel["id"],
            channel["type"],
            channel["guild_id"],
            channel["name"],
            channel["permission_overwrites"]
        ) for channel in result_json
        if channel["type"] != DISCORD_CATEGORY_ID
        and channel["parent_id"] == cid
    ]
    return channels

async def search_user(
    user: str,
    gid: str = guild_id
) -> User:
    token = os.environ.get("TOKEN")
    url = f"https://discord.com/api/v10/guilds/{gid}/members/search?query={user}"
    result = await _discord_request(url, token)
    json = result.json()

    if len(json) == 0:
        return None
    json = json[0]["user"]
    return User(json["id"], json["username"], json["discriminator"], json["global_name"], json["avatar"])
