import os

root_ip_address = "http://localhost:8000" if os.environ.get("LOCAL") == "true" else "https://api.sfucsss.org"
guild_id = "1260652618875797504" if os.environ.get("LOCAL") == "true" else "228761314644852736"
github_org_name = "CSSS-Test-Organization" if os.environ.get("LOCAL") == "true" else "CSSS"

SESSION_ID_LEN = 512
# technically a max of 8 digits https://www.sfu.ca/computing/about/support/tips/sfu-userid.html
COMPUTING_ID_LEN = 32

# see https://support.discord.com/hc/en-us/articles/4407571667351-How-to-Find-User-IDs-for-Law-Enforcement#:~:text=Each%20Discord%20user%20is%20assigned,user%20and%20cannot%20be%20changed.
DISCORD_ID_LEN = 18

# https://github.com/discord/discord-api-docs/blob/main/docs/resources/User.md
DISCORD_NAME_LEN = 32
DISCORD_NICKNAME_LEN = 32

# https://docs.github.com/en/enterprise-server@3.10/admin/identity-and-access-management/iam-configuration-reference/username-considerations-for-external-authentication
GITHUB_USERNAME_LEN = 39
