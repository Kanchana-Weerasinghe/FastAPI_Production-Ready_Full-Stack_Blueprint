import uuid
from typing import Any

import pytest

from app.core.config import config
from app.main import container

FIRST_USER_CREDENTIALS = {"email": "first_user@email.com", "password": "SecurePass123!"}
SECOND_USER_CREDENTIALS = {"email": "second_user@email.com", "password": "SecurePass123!"}


async def test_list_attachments_success(client: Any) -> None:
    """Integration test verifying that an authenticated user can list the attachment records they own."""
    api_client = await client(FIRST_USER_CREDENTIALS["email"], FIRST_USER_CREDENTIALS["password"])
    response = await api_client.get("/v2/attachments/")
    assert response.status_code == 200
    assert "founds" in response.json()


async def test_upload_attachment_success(client: Any) -> None:
    """Integration test verifying that an authenticated user can upload a file with an allowed extension successfully."""
    api_client = await client(FIRST_USER_CREDENTIALS["email"], FIRST_USER_CREDENTIALS["password"])
    response = await api_client.post(
        "/v2/attachments/",
        files={"file": ("test.json", b'{"test": "data"}', "application/json")},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["fileName"] == "test.json"
    assert "id" in data


async def test_upload_attachment_unauthorized(client: Any) -> None:
    """Integration test verifying that unauthenticated users are blocked from uploading attachments, returning 401."""
    api_client = await client()
    response = await api_client.post(
        "/v2/attachments/",
        files={"file": ("test.json", b'{"test": "data"}', "application/json")},
    )
    assert response.status_code == 401


async def test_upload_attachment_invalid_extension(client: Any) -> None:
    """Integration test verifying that trying to upload a file with an disallowed extension (e.g. .txt) returns a 400 Bad Request status."""
    api_client = await client(FIRST_USER_CREDENTIALS["email"], FIRST_USER_CREDENTIALS["password"])
    response = await api_client.post(
        "/v2/attachments/",
        files={"file": ("test.txt", b"invalid file ext", "text/plain")},
    )
    assert response.status_code == 400


async def test_download_attachment_success(client: Any) -> None:
    """Integration test verifying that an authenticated owner can successfully download their uploaded file."""
    api_client = await client(FIRST_USER_CREDENTIALS["email"], FIRST_USER_CREDENTIALS["password"])
    upload_response = await api_client.post(
        "/v2/attachments/",
        files={"file": ("test.json", b'{"test": "data"}', "application/json")},
    )
    file_id = upload_response.json()["id"]

    download_response = await api_client.get(f"/v2/attachments/{file_id}:download")
    assert download_response.status_code == 200
    assert download_response.content == b'{"test": "data"}'


async def test_download_attachment_not_owned(client: Any) -> None:
    """Integration test verifying that downloading an attachment owned by another user is blocked, returning 403 Forbidden."""
    first_client = await client(FIRST_USER_CREDENTIALS["email"], FIRST_USER_CREDENTIALS["password"])
    upload_response = await first_client.post(
        "/v2/attachments/",
        files={"file": ("test.json", b'{"test": "data"}', "application/json")},
    )
    file_id = upload_response.json()["id"]

    second_client = await client(SECOND_USER_CREDENTIALS["email"], SECOND_USER_CREDENTIALS["password"])
    download_response = await second_client.get(f"/v2/attachments/{file_id}:download")
    assert download_response.status_code == 403


async def test_download_attachment_not_found(client: Any) -> None:
    """Integration test verifying that attempting to download a non-existent attachment ID returns a 404 Not Found status."""
    api_client = await client(FIRST_USER_CREDENTIALS["email"], FIRST_USER_CREDENTIALS["password"])
    random_uuid = str(uuid.uuid4())
    response = await api_client.get(f"/v2/attachments/{random_uuid}:download")
    assert response.status_code == 404


async def test_delete_attachment_success(client: Any) -> None:
    """Integration test verifying that an authenticated owner can successfully delete their attachment, removing it from both database and disk."""
    api_client = await client(FIRST_USER_CREDENTIALS["email"], FIRST_USER_CREDENTIALS["password"])
    upload_response = await api_client.post(
        "/v2/attachments/",
        files={"file": ("test.json", b'{"test": "data"}', "application/json")},
    )
    file_id = upload_response.json()["id"]

    delete_response = await api_client.delete(f"/v2/attachments/{file_id}")
    assert delete_response.status_code == 204


async def test_delete_attachment_not_owned(client: Any) -> None:
    """Integration test verifying that trying to delete an attachment owned by another user is blocked, returning a 403 Forbidden status."""
    first_client = await client(FIRST_USER_CREDENTIALS["email"], FIRST_USER_CREDENTIALS["password"])
    upload_response = await first_client.post(
        "/v2/attachments/",
        files={"file": ("test.json", b'{"test": "data"}', "application/json")},
    )
    file_id = upload_response.json()["id"]

    second_client = await client(SECOND_USER_CREDENTIALS["email"], SECOND_USER_CREDENTIALS["password"])
    delete_response = await second_client.delete(f"/v2/attachments/{file_id}")
    assert delete_response.status_code == 403


async def test_list_attachments_pagination_and_search(client: Any) -> None:
    """Integration test verifying that listing attachments supports pagination and fileName search filters."""
    api_client = await client(FIRST_USER_CREDENTIALS["email"], FIRST_USER_CREDENTIALS["password"])
    for i in range(3):
        upload_resp = await api_client.post(
            "/v2/attachments/",
            files={"file": (f"search_test_file_{i}.json", b'{"test": "data"}', "application/json")},
        )
        assert upload_resp.status_code == 201
    response_paginated = await api_client.get("/v2/attachments/?page=1&pageSize=2")
    assert response_paginated.status_code == 200
    data_paginated = response_paginated.json()
    assert len(data_paginated["founds"]) == 2
    response_search = await api_client.get("/v2/attachments/?fileName=search_test_file")
    assert response_search.status_code == 200
    data_search = response_search.json()
    assert len(data_search["founds"]) == 3
    for item in data_search["founds"]:
        assert "search_test_file" in item["fileName"]


async def test_download_attachment_not_found_on_disk(client: Any) -> None:
    """Integration test verifying that trying to download an attachment whose file is missing on disk returns 404."""
    api_client = await client(FIRST_USER_CREDENTIALS["email"], FIRST_USER_CREDENTIALS["password"])
    upload_response = await api_client.post(
        "/v2/attachments/",
        files={"file": ("missing_on_disk.json", b'{"test": "data"}', "application/json")},
    )
    assert upload_response.status_code == 201
    file_id = upload_response.json()["id"]
    attachment = await container.attachments.service().get_by_id(uuid.UUID(file_id))
    container.file_storage().path(attachment.storage_key).unlink()

    download_response = await api_client.get(f"/v2/attachments/{file_id}:download")
    assert download_response.status_code == 404
    assert download_response.json()["code"] == "file_missing"


async def test_upload_response_exposes_download_url_only(client: Any) -> None:
    """Integration test verifying the upload response exposes the authenticated download path and no storage location."""
    api_client = await client(FIRST_USER_CREDENTIALS["email"], FIRST_USER_CREDENTIALS["password"])
    response = await api_client.post(
        "/v2/attachments/",
        files={"file": ("report.json", b"{}", "application/json")},
    )
    data = response.json()
    assert data["downloadUrl"] == f"/v2/attachments/{data['id']}:download"
    assert "fileUrl" not in data
    assert "storageKey" not in data


async def test_uploads_are_not_publicly_served(client: Any) -> None:
    """Integration test verifying stored files cannot be fetched through a static path, bypassing ownership checks."""
    api_client = await client(FIRST_USER_CREDENTIALS["email"], FIRST_USER_CREDENTIALS["password"])
    upload = await api_client.post("/v2/attachments/", files={"file": ("public.json", b"{}", "application/json")})
    attachment = await container.attachments.service().get_by_id(uuid.UUID(upload.json()["id"]))
    anonymous = await client()
    response = await anonymous.get(f"/uploads/{attachment.storage_key}")
    assert response.status_code == 404


async def test_download_sets_safe_headers(client: Any) -> None:
    """Integration test verifying downloads are forced as attachments with MIME sniffing disabled."""
    api_client = await client(FIRST_USER_CREDENTIALS["email"], FIRST_USER_CREDENTIALS["password"])
    upload = await api_client.post("/v2/attachments/", files={"file": ("safe.json", b"{}", "text/html")})
    response = await api_client.get(f"/v2/attachments/{upload.json()['id']}:download")
    assert response.headers["content-disposition"].startswith("attachment;")
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["content-type"].startswith("application/json")


async def test_upload_request_body_too_large(client: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    """Integration test verifying requests whose Content-Length exceeds MAX_REQUEST_BODY_BYTES are rejected with 413."""
    monkeypatch.setattr(config, "MAX_REQUEST_BODY_BYTES", 100)
    api_client = await client(FIRST_USER_CREDENTIALS["email"], FIRST_USER_CREDENTIALS["password"])
    response = await api_client.post(
        "/v2/attachments/",
        files={"file": ("big.json", b"x" * 500, "application/json")},
    )
    assert response.status_code == 413
    assert response.json()["code"] == "payload_too_large"
    assert response.headers["content-type"] == "application/problem+json"
