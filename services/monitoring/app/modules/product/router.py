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
from app.modules.product.application.use_cases import CreateProductCommand, ProductUseCases, UpdateProductCommand
from app.modules.product.domain.value_objects import ProductStatus
from app.modules.product.schemas import ProductCreate, ProductList, ProductResponse, ProductUpdate

# Mounted under /v1 in app/api.py, so these routes are /v1/product/...
router = APIRouter(prefix="/product", tags=["product"], dependencies=[require_access()])

READ_LIMIT = [rate_limit("200/minute")]
WRITE_LIMIT = [rate_limit("60/minute")]
USE_CASES = "product.use_cases"  # built by container.py


@router.post(
    "/",
    status_code=status.HTTP_201_CREATED,
    response_model=ProductResponse,
    operation_id="createProduct",
    summary="Create Product",
    dependencies=WRITE_LIMIT,
)
@inject
async def create_product(
    body: ProductCreate,
    request: Request,
    response: Response,
    use_cases: ProductUseCases = Depends(Provide[USE_CASES]),
) -> ProductResponse:
    product = await use_cases.create(CreateProductCommand(name=body.name, code=body.code))
    response.headers["Location"] = f"{request.url.path.rstrip('/')}/{product.id}"
    return ProductResponse.from_entity(product)


@router.get(
    "/",
    response_model=ProductList,
    operation_id="listProduct",
    summary="List Product",
    dependencies=READ_LIMIT,
)
@inject
async def list_product(
    page: Pagination,  # ?page=1&pageSize=20
    status_filter: Annotated[ProductStatus | None, Query(alias="status")] = None,  # ?status=active
    use_cases: ProductUseCases = Depends(Provide[USE_CASES]),
) -> ProductList:
    result = await use_cases.list(status=status_filter, offset=page.offset, limit=page.page_size)
    return ProductList(
        items=[ProductResponse.from_entity(x) for x in result.items],
        page_info=PageInfo(page=page.page, page_size=page.page_size, total_count=result.total),
    )


@router.get(
    "/{product_id}",
    response_model=ProductResponse,
    operation_id="getProduct",
    summary="Get Product",
    dependencies=READ_LIMIT,
)
@inject
async def get_product(
    product_id: UUID,
    use_cases: ProductUseCases = Depends(Provide[USE_CASES]),
) -> ProductResponse:
    return ProductResponse.from_entity(await use_cases.get(product_id))


@router.patch(
    "/{product_id}",
    response_model=ProductResponse,
    operation_id="updateProduct",
    summary="Update Product",
    dependencies=WRITE_LIMIT,
)
@inject
async def update_product(
    product_id: UUID,
    body: ProductUpdate,
    use_cases: ProductUseCases = Depends(Provide[USE_CASES]),
) -> ProductResponse:
    product = await use_cases.update(product_id, UpdateProductCommand(name=body.name, code=body.code))
    return ProductResponse.from_entity(product)


@router.post(
    "/{product_id}:archive",
    response_model=ProductResponse,
    operation_id="archiveProduct",
    summary="Archive Product",
    dependencies=WRITE_LIMIT,
)
@inject
async def archive_product(
    product_id: UUID,
    use_cases: ProductUseCases = Depends(Provide[USE_CASES]),
) -> ProductResponse:
    return ProductResponse.from_entity(await use_cases.archive(product_id))


@router.post(
    "/{product_id}:restore",
    response_model=ProductResponse,
    operation_id="restoreProduct",
    summary="Restore Product",
    dependencies=WRITE_LIMIT,
)
@inject
async def restore_product(
    product_id: UUID,
    use_cases: ProductUseCases = Depends(Provide[USE_CASES]),
) -> ProductResponse:
    return ProductResponse.from_entity(await use_cases.restore(product_id))


@router.delete(
    "/{product_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    operation_id="deleteProduct",
    summary="Delete Product",
    dependencies=WRITE_LIMIT,
)
@inject
async def delete_product(
    product_id: UUID,
    use_cases: ProductUseCases = Depends(Provide[USE_CASES]),
) -> Response:
    await use_cases.delete(product_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
