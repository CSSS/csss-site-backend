import requests
from requests import Response
import os

from constants import guild_id
from dataclasses import dataclass 
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
            'Authorization': f'Bot {token}',
            'Content-Type': 'application/json',
            'User-Agent' : 'DiscordBot (https://github.com/CSSS/csss-site-backend, 1.0)'
        }
    )
    return result

async def get_channel_members(
    cid: str,
    # TODO: hardcode guild_id (remove it as argument) if we ever refactor this module
    id: str = guild_id
) -> list[GuildMember]:
    channel = await get_channel(cid, id)
    channel_overwrites = channel[0]['permission_overwrites']
    channel_overwrites = dict(map(lambda x: (x['id'], dict(type = x['type'], allow = x['allow'], deny = x['deny'])), channel_overwrites))

    # note that there can exist only one @everyone override, break if found
    if id in channel_overwrites:
        role_everyone_overrides = channel_overwrites[id]
    else:
         role_everyone_overrides = None
    
    role_everyone = await get_role_by_id(id, id)
    base_permission = role_everyone['permissions']

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
            permission &= ~int(role_everyone_overrides['deny'])
            permission |= int(role_everyone_overrides['allow'])

        allow = 0
        deny = 0
        for role in user.roles:
            if role in channel_overwrites:
                allow |= int(channel_overwrites[role]['allow'])
                deny |= int(channel_overwrites[role]['deny'])
        permission &= ~deny
        permission |= allow

        # check member specific perms
        if user.user.id in channel_overwrites:
            # switching of 'deny' and 'allow' intentional
            permission &= ~int(channel_overwrites[user.user.id]['deny'])
            permission |= int(channel_overwrites[user.user.id]['allow'])

        if permission & VIEW_CHANNEL == VIEW_CHANNEL:
            if user not in users_with_access:
                users_with_access.append(user)

    return users_with_access

async def get_channel(
    cid: str,
    id: str = guild_id
) -> Channel:
    token = os.environ.get('TOKEN')
    url = f'https://discord.com/api/v10/guilds/{id}/channels'
    result = await _discord_request(url, token)

    result_json = result.json()
    channel = [channel for channel in result_json if channel['id'] == cid][0]
    channel = Channel(channel['id'], channel['type'], channel['guild_id'], channel['name'], channel['permission_overwrites'])

    return channel

async def get_all_channels(
    id: str = guild_id
) -> list[str]:
    token = os.environ.get('TOKEN')
    url = f'https://discord.com/api/v10/guilds/{id}/channels'
    result = await _discord_request(url, token)

    result_json = result.json()
    channels = [channel for channel in result_json if channel['type'] != DISCORD_CATEGORY_ID]
    channel_names = [channel['name'] for channel in channels]

    return channel_names


async def get_role_name_by_id(
    rid: str,
    id: str = guild_id
) -> str:
    roles = await get_all_roles(id)
    return roles[rid][0]

async def get_role_by_id(
    rid: str,
    id: str = guild_id
) -> dict:
    token = os.environ.get('TOKEN')
    url = f'https://discord.com/api/v10/guilds/{id}/roles'
    result = await _discord_request(url, token)

    result_json = result.json()
    return [role for role in result_json if role['id'] == rid][0]

async def get_user_roles(
    uid: str,
    id: str = guild_id
) -> list[str]:
    token = os.environ.get('TOKEN')
    url = f'https://discord.com/api/v10/guilds/{id}/members/{uid}'
    result = await _discord_request(url, token)

    result_json = result.json()
    return result_json['roles']


async def get_all_roles(
    id: str = guild_id
) ->  dict[str, list[str]]:
    """
    Grabs all roles in a given guild.
    """
    token = os.environ.get('TOKEN')
    url = f'https://discord.com/api/v10/guilds/{id}/roles'
    result = await _discord_request(url, token)

    result_json = result.json()
    roles = [([role['id'], [role['name'], role['permissions']]]) for role in result_json]
    return dict(roles)

async def get_guild_members_with_role(
    rid: str,
    id: str = guild_id
) -> list[GuildMember]:
    token = os.environ.get('TOKEN')
    # base case
    url = f'https://discord.com/api/v10/guilds/{id}/members?limit=1000'
    result = await _discord_request(url, token)

    result_json = result.json()

    matched = [GuildMember(User(user['user']['id'], user['user']['username'], user['user']['discriminator'], user['user']['global_name'], user['user']['avatar']), user['roles'])
                    for user in result_json if rid in user['roles']] 

    last_uid = matched[-1].user.id

    while True:
        url = f'https://discord.com/api/v10/guilds/{id}/members?limit=1000&after={last_uid}'
        result = await _discord_request(url, token)

        result_json = result.json()

        if len(result_json) == 0:
            return matched
        
        res = [GuildMember(User(user['user']['id'], user['user']['username'], user['user']['discriminator'], user['user']['global_name'], user['user']['avatar']), user['roles'])
                    for user in result_json if rid in user['roles']] 
        matched += res


        last_uid = res[-1].user.id
    
async def get_guild_members(
    id: str = guild_id
) -> list[GuildMember]:
    token = os.environ.get('TOKEN')
    # base case
    url = f'https://discord.com/api/v10/guilds/{id}/members?limit=1000'
    result = await _discord_request(url, token)

    result_json = result.json()
    users = [GuildMember(User(user['user']['id'], user['user']['username'], user['user']['discriminator'], user['user']['global_name'], user['user']['avatar']), user['roles']) for user in result_json]
    last_uid = users[-1].user.id

    while True:
        url = f'https://discord.com/api/v10/guilds/{id}/members?limit=1000&after={last_uid}'
        result = await _discord_request(url, token)

        result_json = result.json()
        
        if len(result_json) == 0:
            return users
        
        res = [GuildMember(User(user['user']['id'], user['user']['username'], user['user']['discriminator'], user['user']['global_name'], user['user']['avatar']), user['roles']) for user in result_json]
        users += res

        last_uid = res[-1].user.id

async def get_categories(
    id: str = guild_id
) -> list[str]:
    token = os.environ.get('TOKEN')
    url = f'https://discord.com/api/v10/guilds/{id}/channels'
    result = await _discord_request(url, token)

    result_json = result.json()
    return [category['name'] for category in result_json if category['type'] == DISCORD_CATEGORY_ID]

async def get_channels_by_category_name(
    category_name: str,
    id: str = guild_id
) -> list[Channel]:
    token = os.environ.get('TOKEN')
    url = f'https://discord.com/api/v10/guilds/{id}/channels'
    result = await _discord_request(url, token)

    result_json = result.json()
    # TODO: edge case if there exist duplicate category names, see get_channels_by_category_id()
    category_id = [category['id'] for category in result_json if category['type'] == DISCORD_CATEGORY_ID and category['name'] == category_name][0]
    channels = [Channel(channel['id'], channel['type'], channel['guild_id'], channel['name'], channel['permission_overwrites']) 
                for channel in result_json if channel['type'] != DISCORD_CATEGORY_ID and channel['parent_id'] == category_id]
    return channels

async def get_channels_by_category_id(
    cid: str,
    id: str = guild_id
) -> list[Channel]:
    token = os.environ.get('TOKEN')
    url = f'https://discord.com/api/v10/guilds/{id}/channels'
    result = await _discord_request(url, token)

    result_json = result.json()
    channels = [Channel(channel['id'], channel['type'], channel['guild_id'], channel['name'], channel['permission_overwrites']) 
                for channel in result_json if channel['type'] != DISCORD_CATEGORY_ID and channel['parent_id'] == cid]
    return channels

async def search_user(
    user: str,
    id: str = guild_id
) -> User:
    token = os.environ.get('TOKEN')
    url = f'https://discord.com/api/v10/guilds/{id}/members/search?query={user}'
    result = await _discord_request(url, token)
    json = result.json()
    if len(json) == 0:
        return None
    json = json[0]['user']
    return User(json['id'], json['username'], json['discriminator'], json['global_name'], json['avatar'])