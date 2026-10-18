import uuid
from typing import Any

FIRST_USER_CREDENTIALS = {"email": "first_user@email.com", "password": "SecurePass123!"}
SECOND_USER_CREDENTIALS = {"email": "second_user@email.com", "password": "SecurePass123!"}


async def test_get_todos_list_success(client: Any) -> None:
    """Integration test verifying that an authenticated user can list their seeded Todo items successfully."""
    api_client = await client(FIRST_USER_CREDENTIALS["email"], FIRST_USER_CREDENTIALS["password"])
    response = await api_client.get("/v2/todos/")
    assert response.status_code == 200
    data = response.json()
    assert "founds" in data
    assert data["searchOptions"]["totalCount"] == 16


async def test_get_todos_list_unauthorized(client: Any) -> None:
    """Integration test verifying that unauthenticated requests to list Todos return a 401 Unauthorized status."""
    api_client = await client()
    response = await api_client.get("/v2/todos/")
    assert response.status_code == 401


async def test_create_todo_success(client: Any) -> None:
    """Integration test verifying that an authenticated user can create a new Todo task."""
    api_client = await client(FIRST_USER_CREDENTIALS["email"], FIRST_USER_CREDENTIALS["password"])
    response = await api_client.post(
        "/v2/todos/",
        json={"title": "Integration Test Todo", "description": "Test description"},
    )
    assert response.status_code == 201
    list_response = await api_client.get("/v2/todos/")
    assert list_response.status_code == 200
    assert list_response.json()["searchOptions"]["totalCount"] == 17


async def test_create_todo_unauthorized(client: Any) -> None:
    """Integration test verifying that unauthenticated requests to create a Todo return a 401 Unauthorized status."""
    api_client = await client()
    response = await api_client.post(
        "/v2/todos/",
        json={"title": "Unauthorized Todo"},
    )
    assert response.status_code == 401


async def test_create_todo_validation_error(client: Any) -> None:
    """Integration test verifying that attempting to create a Todo without required fields (e.g. title) raises a 422 Validation Error."""
    api_client = await client(FIRST_USER_CREDENTIALS["email"], FIRST_USER_CREDENTIALS["password"])
    response = await api_client.post(
        "/v2/todos/",
        json={"description": "Missing title"},
    )
    assert response.status_code == 422


async def test_get_todo_detail_success(client: Any) -> None:
    """Integration test verifying that an authenticated user can successfully retrieve the details of a Todo they own."""
    api_client = await client(FIRST_USER_CREDENTIALS["email"], FIRST_USER_CREDENTIALS["password"])
    list_response = await api_client.get("/v2/todos/")
    todo_id = list_response.json()["founds"][0]["id"]
    detail_response = await api_client.get(f"/v2/todos/{todo_id}")
    assert detail_response.status_code == 200
    assert detail_response.json()["id"] == todo_id


async def test_get_todo_detail_not_owned(client: Any) -> None:
    """Integration test verifying that a user cannot retrieve details of a Todo owned by another user, returning 403 Forbidden."""
    first_client = await client(FIRST_USER_CREDENTIALS["email"], FIRST_USER_CREDENTIALS["password"])
    list_response = await first_client.get("/v2/todos/")
    todo_id = list_response.json()["founds"][0]["id"]

    second_client = await client(SECOND_USER_CREDENTIALS["email"], SECOND_USER_CREDENTIALS["password"])
    detail_response = await second_client.get(f"/v2/todos/{todo_id}")
    assert detail_response.status_code == 403


async def test_get_todo_detail_not_found(client: Any) -> None:
    """Integration test verifying that requesting a non-existent Todo ID returns a 404 Not Found status."""
    api_client = await client(FIRST_USER_CREDENTIALS["email"], FIRST_USER_CREDENTIALS["password"])
    random_uuid = str(uuid.uuid4())
    response = await api_client.get(f"/v2/todos/{random_uuid}")
    assert response.status_code == 404


async def test_update_todo_success(client: Any) -> None:
    """Integration test verifying that an authenticated owner can successfully update fields on their Todo task."""
    api_client = await client(FIRST_USER_CREDENTIALS["email"], FIRST_USER_CREDENTIALS["password"])
    list_response = await api_client.get("/v2/todos/")
    todo_id = list_response.json()["founds"][0]["id"]

    update_response = await api_client.patch(
        f"/v2/todos/{todo_id}",
        json={"title": "Updated Todo Title"},
    )
    assert update_response.status_code == 200

    detail_response = await api_client.get(f"/v2/todos/{todo_id}")
    assert detail_response.status_code == 200
    assert detail_response.json()["title"] == "Updated Todo Title"


async def test_update_todo_not_owned(client: Any) -> None:
    """Integration test verifying that updating a Todo owned by another user is blocked and returns a 403 Forbidden status."""
    first_client = await client(FIRST_USER_CREDENTIALS["email"], FIRST_USER_CREDENTIALS["password"])
    list_response = await first_client.get("/v2/todos/")
    todo_id = list_response.json()["founds"][0]["id"]

    second_client = await client(SECOND_USER_CREDENTIALS["email"], SECOND_USER_CREDENTIALS["password"])
    update_response = await second_client.patch(
        f"/v2/todos/{todo_id}",
        json={"title": "Unauthorized Update"},
    )
    assert update_response.status_code == 403


async def test_archive_todo_success(client: Any) -> None:
    """Integration test verifying that an owner can archive their Todo, changing its status and removing it from the default active list."""
    api_client = await client(FIRST_USER_CREDENTIALS["email"], FIRST_USER_CREDENTIALS["password"])
    list_response = await api_client.get("/v2/todos/")
    todo_id = list_response.json()["founds"][0]["id"]

    archive_response = await api_client.post(f"/v2/todos/{todo_id}:archive")
    assert archive_response.status_code == 200

    detail_response = await api_client.get(f"/v2/todos/{todo_id}")
    assert detail_response.status_code == 404


async def test_delete_todo_success(client: Any) -> None:
    """Integration test verifying that an archived Todo task can be permanently deleted by its owner."""
    api_client = await client(FIRST_USER_CREDENTIALS["email"], FIRST_USER_CREDENTIALS["password"])
    list_response = await api_client.get("/v2/todos/")
    todo_id = list_response.json()["founds"][0]["id"]

    archive_response = await api_client.post(f"/v2/todos/{todo_id}:archive")
    assert archive_response.status_code == 200

    delete_response = await api_client.delete(f"/v2/todos/{todo_id}")
    assert delete_response.status_code == 204


async def test_get_todos_list_pagination_and_search(client: Any) -> None:
    """Integration test verifying that listing Todos supports pagination and title search filters."""
    api_client = await client(FIRST_USER_CREDENTIALS["email"], FIRST_USER_CREDENTIALS["password"])
    response_paginated = await api_client.get("/v2/todos/?page=1&pageSize=5")
    assert response_paginated.status_code == 200
    data_paginated = response_paginated.json()
    assert len(data_paginated["founds"]) == 5
    assert data_paginated["searchOptions"]["totalCount"] >= 15
    sample_title = data_paginated["founds"][0]["title"]
    search_query = sample_title[: max(3, len(sample_title) // 2)]
    response_search = await api_client.get(f"/v2/todos/?title={search_query}")
    assert response_search.status_code == 200
    data_search = response_search.json()
    assert len(data_search["founds"]) > 0
    for item in data_search["founds"]:
        assert search_query.lower() in item["title"].lower()


async def test_create_todo_with_another_users_attachment(client: Any) -> None:
    """Integration test verifying a user cannot link (and thereby read) an attachment owned by another user."""
    owner = await client(SECOND_USER_CREDENTIALS["email"], SECOND_USER_CREDENTIALS["password"])
    upload = await owner.post("/v2/attachments/", files={"file": ("private.json", b"{}", "application/json")})
    attachment_id = upload.json()["id"]

    attacker = await client(FIRST_USER_CREDENTIALS["email"], FIRST_USER_CREDENTIALS["password"])
    response = await attacker.post("/v2/todos/", json={"title": "Steal", "attachmentIds": [attachment_id]})
    assert response.status_code == 404
    todos = (await attacker.get("/v2/todos/", params={"title": "Steal"})).json()
    assert todos["searchOptions"]["totalCount"] == 0


async def test_list_todos_rejects_unknown_ordering(client: Any) -> None:
    """Integration test verifying that ordering by a field outside the allow-list is rejected with 422 instead of a 500."""
    api_client = await client(FIRST_USER_CREDENTIALS["email"], FIRST_USER_CREDENTIALS["password"])
    response = await api_client.get("/v2/todos/", params={"ordering": "-user_id"})
    assert response.status_code == 422


async def test_list_todos_allows_listed_ordering(client: Any) -> None:
    """Integration test verifying that an allow-listed ordering field is accepted."""
    api_client = await client(FIRST_USER_CREDENTIALS["email"], FIRST_USER_CREDENTIALS["password"])
    response = await api_client.get("/v2/todos/", params={"ordering": "title"})
    assert response.status_code == 200
    titles = [item["title"] for item in response.json()["founds"]]
    assert titles == sorted(titles)


async def test_list_todos_rejects_page_size_above_maximum(client: Any) -> None:
    """Integration test verifying that page sizes above MAX_PAGE_SIZE (and the old 'all' value) are rejected with 422."""
    api_client = await client(FIRST_USER_CREDENTIALS["email"], FIRST_USER_CREDENTIALS["password"])
    assert (await api_client.get("/v2/todos/", params={"pageSize": 101})).status_code == 422
    assert (await api_client.get("/v2/todos/", params={"pageSize": "all"})).status_code == 422
