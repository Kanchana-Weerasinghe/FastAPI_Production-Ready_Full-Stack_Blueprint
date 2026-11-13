"""
ROUTER (HTTP endpoints): the thin layer between HTTP and the use cases. No business rules here.

For every request:
    1. `require_access()` (on the router) checks the route's `operation_id` against
       config/access-control.json: 401 if not signed in, 403 if not granted. Never check roles here.
    2. `rate_limit(...)` limits calls per client; the schema validates the JSON.
    3. ONE use-case method is called with plain values.
    4. The result is turned into a response schema.

To add an endpoint: copy a function below, give it a NEW camelCase `operation_id` (never rename one
later), then grant that operation_id to roles in config/access-control.json.
"""

from typing import Annotated
from uuid import UUID

from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, Query, Request, Response, status
from platform_kit.access import require_access
from platform_kit.http.pagination import PageInfo, Pagination

from app.core.security import rate_limit
from app.modules.items.application.use_cases import CreateItemCommand, ItemUseCases, UpdateItemCommand
from app.modules.items.domain.value_objects import ItemStatus
from app.modules.items.schemas import ItemCreate, ItemList, ItemResponse, ItemUpdate

# Mounted under /v1 in app/api.py, so these routes are /v1/items/...
router = APIRouter(prefix="/items", tags=["items"], dependencies=[require_access()])

READ_LIMIT = [rate_limit("200/minute")]
WRITE_LIMIT = [rate_limit("60/minute")]
USE_CASES = "items.use_cases"  # built by container.py


@router.post(
    "/",
    status_code=status.HTTP_201_CREATED,
    response_model=ItemResponse,
    operation_id="createItem",
    summary="Create Item",
    dependencies=WRITE_LIMIT,
)
@inject
async def create_item(
    body: ItemCreate,
    request: Request,
    response: Response,
    use_cases: ItemUseCases = Depends(Provide[USE_CASES]),
) -> ItemResponse:
    item = await use_cases.create(CreateItemCommand(name=body.name, code=body.code))
    response.headers["Location"] = f"{request.url.path.rstrip('/')}/{item.id}"
    return ItemResponse.from_entity(item)


@router.get(
    "/",
    response_model=ItemList,
    operation_id="listItems",
    summary="List Items",
    dependencies=READ_LIMIT,
)
@inject
async def list_items(
    page: Pagination,  # ?page=1&pageSize=20
    status_filter: Annotated[ItemStatus | None, Query(alias="status")] = None,  # ?status=active
    use_cases: ItemUseCases = Depends(Provide[USE_CASES]),
) -> ItemList:
    result = await use_cases.list(status=status_filter, offset=page.offset, limit=page.page_size)
    return ItemList(
        items=[ItemResponse.from_entity(x) for x in result.items],
        page_info=PageInfo(page=page.page, page_size=page.page_size, total_count=result.total),
    )


@router.get(
    "/{item_id}",
    response_model=ItemResponse,
    operation_id="getItem",
    summary="Get Item",
    dependencies=READ_LIMIT,
)
@inject
async def get_item(
    item_id: UUID,
    use_cases: ItemUseCases = Depends(Provide[USE_CASES]),
) -> ItemResponse:
    return ItemResponse.from_entity(await use_cases.get(item_id))


@router.patch(
    "/{item_id}",
    response_model=ItemResponse,
    operation_id="updateItem",
    summary="Update Item",
    dependencies=WRITE_LIMIT,
)
@inject
async def update_item(
    item_id: UUID,
    body: ItemUpdate,
    use_cases: ItemUseCases = Depends(Provide[USE_CASES]),
) -> ItemResponse:
    item = await use_cases.update(item_id, UpdateItemCommand(name=body.name, code=body.code))
    return ItemResponse.from_entity(item)


@router.post(
    "/{item_id}:archive",
    response_model=ItemResponse,
    operation_id="archiveItem",
    summary="Archive Item",
    dependencies=WRITE_LIMIT,
)
@inject
async def archive_item(
    item_id: UUID,
    use_cases: ItemUseCases = Depends(Provide[USE_CASES]),
) -> ItemResponse:
    return ItemResponse.from_entity(await use_cases.archive(item_id))


@router.post(
    "/{item_id}:restore",
    response_model=ItemResponse,
    operation_id="restoreItem",
    summary="Restore Item",
    dependencies=WRITE_LIMIT,
)
@inject
async def restore_item(
    item_id: UUID,
    use_cases: ItemUseCases = Depends(Provide[USE_CASES]),
) -> ItemResponse:
    return ItemResponse.from_entity(await use_cases.restore(item_id))


@router.delete(
    "/{item_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    operation_id="deleteItem",
    summary="Delete Item",
    dependencies=WRITE_LIMIT,
)
@inject
async def delete_item(
    item_id: UUID,
    use_cases: ItemUseCases = Depends(Provide[USE_CASES]),
) -> Response:
    await use_cases.delete(item_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
