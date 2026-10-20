"""End-to-end behaviour of /v1/acquisition-jobs: HTTP contract, auth, ownership, rules, concurrency."""

import uuid

from httpx import AsyncClient

from tests.integration.conftest import TokenFactory

BASE = "/v1/acquisition-jobs/"
BODY = {"name": "Catalogue crawl", "sourceType": "web", "sourceUri": "https://example.org/catalogue", "maxAttempts": 2}
WORKER = "acquisition_worker"


async def _create(client: AsyncClient, headers: dict[str, str], **overrides: object) -> dict[str, object]:
    response = await client.post(BASE, json={**BODY, **overrides}, headers=headers)
    assert response.status_code == 201, response.text
    return dict(response.json())


async def test_health_probes(client: AsyncClient) -> None:
    assert (await client.get("/health/live")).status_code == 200
    ready = await client.get("/health/ready")
    assert ready.status_code == 200
    assert ready.json()["database"] == "up"


async def test_requests_without_valid_token_are_rejected(client: AsyncClient, auth: TokenFactory) -> None:
    assert (await client.get(BASE)).status_code == 401
    assert (await client.get(BASE, headers={"Authorization": "Bearer garbage"})).status_code == 401
    refresh = auth(type="refresh")
    response = await client.get(BASE, headers=refresh)
    assert response.status_code == 401
    assert response.headers["content-type"].startswith("application/problem+json")


async def test_create_and_get_job(client: AsyncClient, auth: TokenFactory) -> None:
    owner = auth()
    response = await client.post(BASE, json=BODY, headers=owner)
    assert response.status_code == 201
    job = response.json()
    assert job["status"] == "queued"
    assert job["attempts"] == 0
    assert response.headers["Location"].endswith(job["id"])
    assert response.headers["ETag"] == 'W/"1"'
    assert response.headers["X-Request-ID"]

    fetched = await client.get(f"{BASE}{job['id']}", headers=owner)
    assert fetched.status_code == 200
    assert fetched.json()["name"] == "Catalogue crawl"


async def test_business_rule_violations_are_problem_details(client: AsyncClient, auth: TokenFactory) -> None:
    response = await client.post(
        BASE, json={**BODY, "sourceType": "api", "sourceUri": "http://insecure.example.com"}, headers=auth()
    )
    assert response.status_code == 422
    assert response.json()["code"] == "invalid_source"

    response = await client.post(BASE, json={**BODY, "maxAttempts": 50}, headers=auth())
    assert response.status_code == 422
    assert response.json()["code"] == "validation_failed"


async def test_jobs_are_private_to_their_owner(client: AsyncClient, auth: TokenFactory) -> None:
    job = await _create(client, auth())
    stranger = auth()
    assert (await client.get(f"{BASE}{job['id']}", headers=stranger)).status_code == 404
    assert (await client.post(f"{BASE}{job['id']}:cancel", headers=stranger)).status_code == 404
    listed = (await client.get(BASE, headers=stranger)).json()
    assert all(item["id"] != job["id"] for item in listed["items"])
    assert (await client.get(f"{BASE}{job['id']}", headers=auth(role="admin"))).status_code == 200


async def test_worker_lifecycle_and_retry(client: AsyncClient, auth: TokenFactory) -> None:
    owner, worker = auth(user_id=uuid.uuid4()), auth(role=WORKER)
    job = await _create(client, owner)
    url = f"{BASE}{job['id']}"

    assert (await client.post(f"{url}:start", headers=owner)).status_code == 403  # owners are not workers
    assert (await client.post(f"{url}:start", headers=worker)).json()["status"] == "running"
    failed = (await client.post(f"{url}:fail", json={"reason": "Vendor returned 503"}, headers=worker)).json()
    assert failed["status"] == "failed"
    assert failed["canRetry"] is True

    assert (await client.post(f"{url}:retry", headers=owner)).json()["status"] == "queued"
    await client.post(f"{url}:start", headers=worker)
    progress = await client.post(f"{url}:progress", json={"records": 250}, headers=worker)
    assert progress.json()["recordsCollected"] == 250
    done = (await client.post(f"{url}:complete", headers=worker)).json()
    assert done["status"] == "completed"
    assert done["attempts"] == 2

    conflict = await client.post(f"{url}:cancel", headers=owner)
    assert conflict.status_code == 409
    assert conflict.json()["code"] == "invalid_status_transition"


async def test_retry_limit(client: AsyncClient, auth: TokenFactory) -> None:
    owner, worker = auth(), auth(role=WORKER)
    job = await _create(client, owner, maxAttempts=1)
    url = f"{BASE}{job['id']}"
    await client.post(f"{url}:start", headers=worker)
    await client.post(f"{url}:fail", json={"reason": "Blocked by robots.txt"}, headers=worker)
    response = await client.post(f"{url}:retry", headers=owner)
    assert response.status_code == 409
    assert response.json()["code"] == "retry_limit_reached"


async def test_if_match_protects_against_lost_updates(client: AsyncClient, auth: TokenFactory) -> None:
    owner = auth()
    job = await _create(client, owner)
    url = f"{BASE}{job['id']}"
    stale = await client.post(f"{url}:cancel", headers={**owner, "If-Match": 'W/"99"'})
    assert stale.status_code == 412
    assert stale.json()["current_etag"] == 'W/"1"'
    ok = await client.post(f"{url}:cancel", headers={**owner, "If-Match": 'W/"1"'})
    assert ok.status_code == 200
    assert ok.headers["ETag"] == 'W/"2"'


async def test_active_job_limit_per_owner(client: AsyncClient, auth: TokenFactory) -> None:
    owner = auth(user_id=uuid.uuid4())
    for _ in range(3):  # ACTIVE_JOB_LIMIT_PER_OWNER=3 in the test environment
        await _create(client, owner)
    response = await client.post(BASE, json=BODY, headers=owner)
    assert response.status_code == 409
    assert response.json()["code"] == "active_job_limit_reached"


async def test_list_filters_and_paginates(client: AsyncClient, auth: TokenFactory) -> None:
    owner = auth(user_id=uuid.uuid4())
    first = await _create(client, owner)
    await _create(client, owner)
    await client.post(f"{BASE}{first['id']}:cancel", headers=owner)

    page = (await client.get(BASE, params={"pageSize": 1}, headers=owner)).json()
    assert len(page["items"]) == 1
    assert page["pageInfo"]["totalCount"] == 2

    cancelled = (await client.get(BASE, params={"status": "cancelled"}, headers=owner)).json()
    assert [item["id"] for item in cancelled["items"]] == [first["id"]]

    too_big = await client.get(BASE, params={"pageSize": 500}, headers=owner)
    assert too_big.status_code == 422
