from typing import Annotated, Any
from uuid import UUID

from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, Query, UploadFile, status
from fastapi.responses import FileResponse, RedirectResponse

from app.core.security import rate_limit
from app.modules.attachments.domain.entities import AttachmentRecord
from app.modules.attachments.schemas import Attachment, AttachmentListResponse, FindAttachment
from app.modules.attachments.service import AttachmentService
from app.modules.auth.dependencies import CurrentUserDep, check_ownership

router = APIRouter(tags=["attachments"])

AttachmentServiceDep = Annotated[AttachmentService, Depends(Provide["attachments.service"])]
OwnedAttachmentDep = Annotated[AttachmentRecord, Depends(check_ownership("attachments.service", "_file_id"))]


@router.post(
    "/attachments/",
    status_code=status.HTTP_201_CREATED,
    response_model=Attachment,
    summary="Upload Attachment",
    dependencies=[rate_limit("5/minute")],
)
@inject
async def upload_attachment(
    file: UploadFile,
    service: AttachmentServiceDep,
    current_user: CurrentUserDep,
) -> AttachmentRecord:
    """Uploads a file and creates an unlinked attachment record."""
    return await service.add_attachment(file.file, file.filename, file.content_type, current_user)


@router.delete(
    "/attachments/{_file_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete Attachment",
    dependencies=[rate_limit("20/minute")],
)
@inject
async def delete_attachment(
    _file_id: UUID,
    service: AttachmentServiceDep,
    attachment: OwnedAttachmentDep,
) -> None:
    """Deletes an attachment record; the stored file is removed after the transaction commits."""
    await service.remove(attachment)


@router.get(
    "/attachments/",
    response_model=AttachmentListResponse,
    summary="List Attachments",
    dependencies=[rate_limit("50/minute")],
)
@inject
async def get_user_attachments(
    find_query: Annotated[FindAttachment, Query()],
    service: AttachmentServiceDep,
    current_user: CurrentUserDep,
) -> Any:
    """Retrieves a paginated list of all attachments owned by the current user."""
    find_query_dict = find_query.model_dump(exclude_none=True)
    find_query_dict["user_id__eq"] = current_user.id
    return await service.get_list(find_query_dict)


@router.get(
    "/attachments/{_file_id}:download",
    summary="Download Attachment",
    dependencies=[rate_limit("40/minute")],
    response_model=None,
)
@inject
async def download_attachment(
    _file_id: UUID,
    service: AttachmentServiceDep,
    attachment: OwnedAttachmentDep,
) -> FileResponse | RedirectResponse:
    """
    Downloads the file (always as an attachment, never rendered inline): redirects to a short-lived
    pre-signed URL with object storage, or streams it from local storage.
    """
    target = await service.resolve_download(attachment)
    if isinstance(target, str):
        return RedirectResponse(target, status_code=307, headers={"Cache-Control": "no-store"})
    file_path = target
    return FileResponse(
        path=file_path,
        filename=attachment.file_name,
        media_type=attachment.file_type,
        content_disposition_type="attachment",
        headers={"X-Content-Type-Options": "nosniff"},
    )
