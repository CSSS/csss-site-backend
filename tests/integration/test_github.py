import pytest

import github.internals

# NOTE: must export API key to use github api (mostly...)

@pytest.mark.asyncio
async def test__list_users():
    member_list = await github.internals.list_members()
    print(member_list)

@pytest.mark.asyncio
async def test__get_user_by_name():
    user = await github.internals.get_user_by_username("EarthenSky")
    print(user)

    user2 = await github.internals.get_user_by_username("jamieklo")
    print(user2)

    user3 = await github.internals.get_user_by_username("")
    assert user3 is None
    print(user3)

    user4 = await github.internals.get_user_by_username("asfgkahdgOO_OPPEdkdhghk57777777777")
    assert user4 is None
    print(user4)
