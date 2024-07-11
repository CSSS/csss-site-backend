import requests
import json
import os

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request
from fastapi.responses import RedirectResponse, JSONResponse

# ----------------------- #
# api

router = APIRouter(
    prefix="/discord",
    tags=["discord"],
)

@router.get(
    "/channels",
    description="Grabs all channels in a guild"
)
async def get_channels(
    id: str
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
    #categories = list(filter(lambda x: x['type'] ==  4), json)
    channels = list(filter(lambda x: x['type'] != 4, result_json))
    channel_names = list(map(lambda x: x['name'], channels))

    return list(map(lambda x: {"channel_name" : x}, channel_names))