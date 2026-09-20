import datetime

import pytest
from fastapi import status
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def test__admin_delete_honorary_member(admin_client: AsyncClient):
    create_response = await admin_client.post(
        "/api/honorary",
        json=[
            {
                "name": "Test Honorary Member",
                "start_date": datetime.date.today().isoformat(),
            }
        ],
    )
    assert create_response.status_code == status.HTTP_200_OK
    term_id = create_response.json()[0]["id"]

    delete_response = await admin_client.delete(f"/api/honorary/{term_id}")
    assert delete_response.status_code == status.HTTP_204_NO_CONTENT
    assert delete_response.content == b""
