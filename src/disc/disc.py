import requests
import json
import os

from constants import guild_id

#todo remove unused imports
from fastapi import APIRouter

# ----------------------- #
# api

DISCORD_CATEGORY_ID = 4

router = APIRouter(
    prefix="/discord",
    tags=["discord"],
)

@router.get(
    "/channels",
    description="Grabs all channels in a guild"
)
async def get_channels(
    id: str = guild_id
):
    tok = os.environ.get('TOKEN')
    url = f'https://discord.com/api/v10/guilds/{id}/channels'
    result = requests.get(
        url,
        headers={
            'Authorization': f'Bot {tok}',
            'Content-Type': 'application/json',
            'User-Agent' : 'DiscordBot (https://github.com/CSSS/csss-site-backend, 1.0)'
        }
    )

    result_json = result.json()
    channels = list(filter(lambda x: x['type'] != DISCORD_CATEGORY_ID, result_json))
    channel_names = list(map(lambda x: x['name'], channels))

    return list(map(lambda x: {"channel_name" : x}, channel_names))

@router.get(
    "/category",
    description="Grabs channels by category"
)
async def get_categories(
    id: str = guild_id
):
    tok = os.environ.get('TOKEN')
    url = f'https://discord.com/api/v10/guilds/{id}/channels'
    result = requests.get(
        url,
        headers={
            'Authorization': f'Bot {tok}',
            'Content-Type': 'application/json',
            'User-Agent' : 'DiscordBot (https://github.com/CSSS/csss-site-backend, 1.0)'
        }
    )

    result_json = result.json()
    categories = list(filter(lambda x: x['type'] == DISCORD_CATEGORY_ID, result_json))
    return list(map(lambda x: x['name'], categories)) 


async def get_channels_by_category_name(
    category_name: str,
    id: str = guild_id
):
    tok = os.environ.get('TOKEN')
    url = f'https://discord.com/api/v10/guilds/{id}/channels'
    result = requests.get(
        url,
        headers={
            'Authorization': f'Bot {tok}',
            'Content-Type': 'application/json',
            'User-Agent' : 'DiscordBot (https://github.com/CSSS/csss-site-backend, 1.0)'
        }
    )

    result_json = result.json()
    # TODO: edge case if there exist duplicate category names, see get_channels_by_category_id()
    category_id = list(filter(lambda x: x['type'] == DISCORD_CATEGORY_ID and x['name'] == category_name, result_json))[0]['id']
    channels = list(filter(lambda x: x['type'] != DISCORD_CATEGORY_ID and x['parent_id'] == category_id, result_json))
    return list(map(lambda x: x['name'], channels))
    


async def get_channels_by_category_id(
    cid: str,
    id: str = guild_id
):
    tok = os.environ.get('TOKEN')
    url = f'https://discord.com/api/v10/guilds/{id}/channels'
    result = requests.get(
        url,
        headers={
            'Authorization': f'Bot {tok}',
            'Content-Type': 'application/json',
            'User-Agent' : 'DiscordBot (https://github.com/CSSS/csss-site-backend, 1.0)'
        }
    )

    result_json = result.json()
    categories = list(filter(lambda x: x['type'] != DISCORD_CATEGORY_ID and x['parent_id'] == cid, result_json))
    return list(map(lambda x: x['name'], categories))
    

        



