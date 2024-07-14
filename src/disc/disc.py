import requests
from requests import Response
import os

from constants import guild_id

# ----------------------- #
# api

DISCORD_CATEGORY_ID = 4
ADMINISTRATOR = 1 << 3
VIEW_CHANNEL = 1 << 10

class User:
    def __init__(self, id: str, username: str, discriminator: str, global_name: str=None, avatar: str=None) -> None:
        self.id = id
        self.username = username
        self.discriminator = discriminator
        self.global_name = global_name
        self.avatar = avatar
    
    def __str__(self) -> str:
        return f"{self.username}, {self.id}"
    
    def __repr__(self) -> str:
        return f"{self.username}, {self.id}"

class GuildMember:
    def __init__(self, user: User = None, roles: list[str] = None) -> None:
        self.user = user
        self.roles = roles
    
    def __str__(self) -> str:
        return f"{self.user.id}, {self.user.username}, {str(self.roles)}"

    def __repr__(self) -> str:
        return f"{self.user.username}"

async def discord_request(
    url: str,
    tok: str
) -> Response:
    result = requests.get(
        url,
        headers={
            'Authorization': f'Bot {tok}',
            'Content-Type': 'application/json',
            'User-Agent' : 'DiscordBot (https://github.com/CSSS/csss-site-backend, 1.0)'
        }
    )
    return result

async def get_channel_members(
    cid: str,
    id: str = guild_id
) -> list:
    channel = await get_channel(cid, id)
    channel_overwrites = channel[0]['permission_overwrites']
    channel_overwrites = dict(map(lambda x: (x['id'], dict(type = x['type'], allow = x['allow'], deny = x['deny'])), channel_overwrites))

    # note that there can exist only one @everyone override, break if found
    if id in channel_overwrites:
        role_everyone_overrides = channel_overwrites[id]
    else:
         role_everyone_overrides = None
    
    role_everyone = await get_role_by_id(id, id)
    base_permission = role_everyone[0]['permissions']

    users = await get_guild_members(guild_id)
    roles = await get_all_roles(guild_id)

    users_with_access = []
    # note string conversion to int
    for user in users:
        permission = int(base_permission)
        print()
        # compute base permission
        for role in user[2]:
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
        for role in user[2]:
            if role in channel_overwrites:
                allow |= int(channel_overwrites[role]['allow'])
                deny |= int(channel_overwrites[role]['deny'])
        permission &= ~deny
        permission |= allow

        # check member specific perms
        if user[1] in channel_overwrites:
            # switching of 'deny' and 'allow' intentional
            permission &= ~int(channel_overwrites[user[1]]['deny'])
            permission |= int(channel_overwrites[user[1]]['allow'])

        if permission & VIEW_CHANNEL == VIEW_CHANNEL:
            if user not in users_with_access:
                users_with_access.append(user)

    return users_with_access

async def get_channel(
    cid: str,
    id: str = guild_id
) -> list:
    tok = os.environ.get('TOKEN')
    url = f'https://discord.com/api/v10/guilds/{id}/channels'
    result = await discord_request(url, tok)

    result_json = result.json()
    channel = list(filter(lambda x: x['id'] == cid, result_json))

    return channel

async def get_channels(
    id: str = guild_id
) -> list[str]:
    tok = os.environ.get('TOKEN')
    url = f'https://discord.com/api/v10/guilds/{id}/channels'
    result = await discord_request(url, tok)

    result_json = result.json()
    channels = list(filter(lambda x: x['type'] != DISCORD_CATEGORY_ID, result_json))
    channel_names = list(map(lambda x: x['name'], channels))

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
    tok = os.environ.get('TOKEN')
    url = f'https://discord.com/api/v10/guilds/{id}/roles'
    result = await discord_request(url, tok)

    json_s = result.json()
    return list(filter(lambda x: x['id'] == guild_id, json_s))[0]

async def get_user_roles(
    uid: str,
    id: str = guild_id
) -> list[str]:
    tok = os.environ.get('TOKEN')
    url = f'https://discord.com/api/v10/guilds/{id}/members/{uid}'
    result = await discord_request(url, tok)

    json_s = result.json()
    return json_s['roles']


async def get_all_roles(
    id: str = guild_id
) ->  dict[str, list[str]]:
    tok = os.environ.get('TOKEN')
    url = f'https://discord.com/api/v10/guilds/{id}/roles'
    result = await discord_request(url, tok)

    json_s = result.json()
    roles = list(map(lambda x: ([x['id'], [x['name'], x['permissions']]]), json_s))
    return dict(roles)

async def get_guild_members_with_role(
    rid: str,
    id: str = guild_id
) -> list[GuildMember]:
    tok = os.environ.get('TOKEN')
    # base case
    url = f'https://discord.com/api/v10/guilds/{id}/members?limit=1'
    result = await discord_request(url, tok)

    json_s = result.json()

    res = list(map(lambda x: GuildMember(User(x['user']['id'], x['user']['username'], x['user']['discriminator'], x['user']['global_name'], x['user']['avatar']), x['roles']),json_s))
    matched = list(filter(lambda x: rid in x.roles, res))

    last_uid = res[-1].user.id

    # loop
    while True:
        url = f'https://discord.com/api/v10/guilds/{id}/members?limit=1&after={last_uid}'
        result = await discord_request(url, tok)

        json_s = result.json()
        res = list(map(lambda x: GuildMember(User(x['user']['id'], x['user']['username'], x['user']['discriminator'], x['user']['global_name'], x['user']['avatar']), x['roles']),json_s))
        match = list(filter(lambda x: rid in x.roles, res))
        matched = [*matched, *match]

        if res == []:
            break

        last_uid = res[-1].user.id
    return matched
    
async def get_guild_members(
    id: str = guild_id
) -> list[GuildMember]:
    tok = os.environ.get('TOKEN')
    # base case
    url = f'https://discord.com/api/v10/guilds/{id}/members?limit=1000'
    result = await discord_request(url, tok)

    json_s = result.json()
    
    users = list(map(lambda x: GuildMember(User(x['user']['id'], x['user']['username'], x['user']['discriminator'], x['user']['global_name'], x['user']['avatar']), x['roles']),json_s))
    last_uid = users[-1].user.id

    # loop
    while True:
        url = f'https://discord.com/api/v10/guilds/{id}/members?limit=1000&after={last_uid}'
        result = await discord_request(url, tok)

        json_s = result.json()
        res = list(map(lambda x: GuildMember(User(x['user']['id'], x['user']['username'], x['user']['discriminator'], x['user']['global_name'], x['user']['avatar']), x['roles']),json_s))
        users = [*users, *res]

        if res == []:
            break

        last_uid = res[-1].user.id
    return users

async def get_categories(
    id: str = guild_id
) -> list[str]:
    tok = os.environ.get('TOKEN')
    url = f'https://discord.com/api/v10/guilds/{id}/channels'
    result = await discord_request(url, tok)

    result_json = result.json()
    categories = list(filter(lambda x: x['type'] == DISCORD_CATEGORY_ID, result_json))
    return list(map(lambda x: x['name'], categories)) 

async def get_channels_by_category_name(
    category_name: str,
    id: str = guild_id
) -> list[str]:
    tok = os.environ.get('TOKEN')
    url = f'https://discord.com/api/v10/guilds/{id}/channels'
    result = await discord_request(url, tok)

    result_json = result.json()
    # TODO: edge case if there exist duplicate category names, see get_channels_by_category_id()
    category_id = list(filter(lambda x: x['type'] == DISCORD_CATEGORY_ID and x['name'] == category_name, result_json))[0]['id']
    channels = list(filter(lambda x: x['type'] != DISCORD_CATEGORY_ID and x['parent_id'] == category_id, result_json))
    return list(map(lambda x: x['name'], channels))

async def get_channels_by_category_id(
    cid: str,
    id: str = guild_id
) -> list[str]:
    tok = os.environ.get('TOKEN')
    url = f'https://discord.com/api/v10/guilds/{id}/channels'
    result = await discord_request(url, tok)

    result_json = result.json()
    categories = list(filter(lambda x: x['type'] != DISCORD_CATEGORY_ID and x['parent_id'] == cid, result_json))
    return list(map(lambda x: x['name'], categories))

async def search_user(
    user: str,
    id: str = guild_id
) -> User:
    tok = os.environ.get('TOKEN')
    url = f'https://discord.com/api/v10/guilds/{id}/members/search?query={user}'
    result = await discord_request(url, tok)
    json = result.json()[0]['user']
    user = User(json['id'], json['username'], json['discriminator'], json['global_name'], json['avatar'])
    return user