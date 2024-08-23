from dataclasses import dataclass

@dataclass
class GithubUser:
    username: str
    id: int
    name: str

@dataclass
class GithubTeam:
    id: int
    url: str
    name: str
    # slugs are the space-free special names that github likes to use
    slug: str

@dataclass
class GithubUserPermissions:
    # this class should store all the possible permissions a user might have

    # used to connect the user to their officer info
    username: str

    # which github teams they're in
    teams: list[str]
