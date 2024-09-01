import os
from dataclasses import dataclass
from time import sleep

import requests
from constants import ACTIVE_GUILD_ID
from requests import Response

# ----------------------- #
# api

DISCORD_CATEGORY_ID = 4
ADMINISTRATOR = 0b1000
VIEW_CHANNEL = 0b0010_0000_0000

# this is the "Application ID"
TOKEN = os.environ.get("DISCORD_TOKEN")

@dataclass
class User:
    id: str
    # this is the normal username
    username: str
    # Discriminators are what used to be the #xxxx after a discord username. Accounts which haven't
    # migrated over yet have them still.
    # For accounts that don't have one, it's '0'
    discriminator: str
    # this is the server-nickname
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
    gid: str = ACTIVE_GUILD_ID
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

    users = await get_guild_members(gid)
    roles = await get_all_roles(gid)

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
    gid: str = ACTIVE_GUILD_ID
) -> Channel | None:
    url = f"https://discord.com/api/v10/guilds/{gid}/channels"
    result = await _discord_request(url, TOKEN)

    result_json = result.json()
    channel = next((channel for channel in result_json if channel["id"] == cid), None)
    if channel is None:
        return None
    else:
        return Channel(channel["id"], channel["type"], channel["guild_id"], channel["name"], channel["permission_overwrites"])

async def get_all_channels(
    gid: str = ACTIVE_GUILD_ID
) -> list[str]:
    url = f"https://discord.com/api/v10/guilds/{gid}/channels"
    result = await _discord_request(url, TOKEN)

    result_json = result.json()
    channels = [channel for channel in result_json if channel["type"] != DISCORD_CATEGORY_ID]
    channel_names = [channel["name"] for channel in channels]

    return channel_names

async def get_role_name_by_id(
    rid: str,
    gid: str = ACTIVE_GUILD_ID
) -> str:
    roles = await get_all_roles(gid)
    return roles[rid][0]

async def get_role_by_id(
    rid: str,
    gid: str = ACTIVE_GUILD_ID
) -> dict | None:
    url = f"https://discord.com/api/v10/guilds/{gid}/roles"
    result = await _discord_request(url, TOKEN)

    result_json = result.json()
    return next((role for role in result_json if role["id"] == rid), None)

async def get_user_roles(
    uid: str,
    gid: str = ACTIVE_GUILD_ID
) -> list[str]:
    url = f"https://discord.com/api/v10/guilds/{gid}/members/{uid}"
    result = await _discord_request(url, TOKEN)

    result_json = result.json()
    return result_json["roles"]

async def get_all_roles(
    gid: str = ACTIVE_GUILD_ID
) ->  dict[str, list[str]]:
    """
    Grabs all roles in a given guild.
    """
    url = f"https://discord.com/api/v10/guilds/{gid}/roles"
    result = await _discord_request(url, TOKEN)

    result_json = result.json()
    roles = [([role["id"], [role["name"], role["permissions"]]]) for role in result_json]
    return dict(roles)

async def get_guild_members_with_role(
    rid: str,
    gid: str = ACTIVE_GUILD_ID
) -> list[GuildMember]:
    # base case
    url = f"https://discord.com/api/v10/guilds/{gid}/members?limit=1000"
    result = await _discord_request(url, TOKEN)

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
        result = await _discord_request(url, TOKEN)

        result_json = result.json()

        if len(result_json) == 0:
            return matched

        res = [GuildMember(User(user["user"]["id"], user["user"]["username"], user["user"]["discriminator"], user["user"]["global_name"], user["user"]["avatar"]), user["roles"])
                    for user in result_json if rid in user["roles"]]
        matched += res

        last_uid = res[-1].user.id

async def get_guild_members(
    gid: str = ACTIVE_GUILD_ID
) -> list[GuildMember]:
    # base case
    url = f"https://discord.com/api/v10/guilds/{gid}/members?limit=1000"
    result = await _discord_request(url, TOKEN)

    if result.status_code != 200:
        raise Exception(f"Got unexpected error result: {result.json()}")

    users = [
        GuildMember(
            User(
                user["user"]["id"],
                user["user"]["username"],
                user["user"]["discriminator"],
                user["user"]["global_name"],
                user["user"]["avatar"],
            ),
            user["roles"]
        ) for user in result.json()
    ]
    last_uid = users[-1].user.id

    while True:
        url = f"https://discord.com/api/v10/guilds/{gid}/members?limit=1000&after={last_uid}"
        result = await _discord_request(url, TOKEN)

        result_json = result.json()
        if len(result_json) == 0:
            return users

        res = [
            GuildMember(
                User(
                    user["user"]["id"],
                    user["user"]["username"],
                    user["user"]["discriminator"],
                    user["user"]["global_name"],
                    user["user"]["avatar"],
                ),
                user["roles"]
            ) for user in result_json
        ]
        users += res

        last_uid = res[-1].user.id

async def get_categories(
    gid: str = ACTIVE_GUILD_ID
) -> list[str]:
    url = f"https://discord.com/api/v10/guilds/{gid}/channels"
    result = await _discord_request(url, TOKEN)

    result_json = result.json()
    return [category["name"] for category in result_json if category["type"] == DISCORD_CATEGORY_ID]

async def get_channels_by_category_name(
    category_name: str,
    gid: str = ACTIVE_GUILD_ID
) -> list[Channel]:
    url = f"https://discord.com/api/v10/guilds/{gid}/channels"
    result = await _discord_request(url, TOKEN)

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
    gid: str = ACTIVE_GUILD_ID
) -> list[Channel]:
    url = f"https://discord.com/api/v10/guilds/{gid}/channels"
    result = await _discord_request(url, TOKEN)

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
    starts_with: str,
    limit: int = 1,
    gid: str = ACTIVE_GUILD_ID
) -> list[User]:
    """
    Returns a list of User objects "whose username or nickname starts with a provided string"
    """
    if starts_with == "":
        raise ValueError("starts_with must be non-empty string; use get_guild_members instead if desired.")

    url = f"https://discord.com/api/v10/guilds/{gid}/members/search?query={starts_with}&limit={limit}"

    result = await _discord_request(url, TOKEN)
    return [
        User(
            entry["user"]["id"],
            entry["user"]["username"],
            entry["user"]["discriminator"],
            entry["user"]["global_name"],
            entry["user"]["avatar"]
        ) for entry in result.json()
    ]

async def search_username(
    username_starts_with: str,
    gid: str = ACTIVE_GUILD_ID
) -> list[User]:
    """
    Returns a list of User objects whose username starts with a provided string.

    Will not return a user with a non-zero descriminator -> these users must update their discord version!
    """
    # if there are more than 100 users with the same nickname as the "username_starts_with" string, this may fail
    user_list = await search_user(username_starts_with, 99, gid)
    return [
        user for user in user_list
        if user.username.startswith(username_starts_with)
        and user.discriminator == "0"
    ]
