import pytest

from discord import discord


# NOTE: must perform setup as described in the csss-site-backend wiki
@pytest.mark.asyncio
async def test__list_users():
    guild_members = await discord.get_guild_members()
    print(guild_members)
