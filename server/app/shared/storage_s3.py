import uuid
from pathlib import Path
from typing import Any, BinaryIO
from urllib.parse import quote

import boto3
from botocore.config import Config as BotoConfig
from botocore.exceptions import ClientError
from starlette.concurrency import run_in_threadpool

from app.core.config import config
from app.core.errors import PayloadTooLargeError
from app.shared.storage import new_storage_key


class _LimitedReader:
    """File-like wrapper that counts bytes and aborts the upload once `max_bytes` is exceeded."""

    def __init__(self, source: BinaryIO, max_bytes: int) -> None:
        self._source = source
        self._max_bytes = max_bytes
        self.size = 0

    def read(self, size: int = -1) -> bytes:
        chunk = self._source.read(size)
        self.size += len(chunk)
        if self.size > self._max_bytes:
            raise PayloadTooLargeError(detail=f"File exceeds the {self._max_bytes} byte limit")
        return chunk


class S3FileStorage:
    """
    `FileStorage` backed by S3 or any S3-compatible service (MinIO, Cloudflare R2, ...).

    Keeps app instances stateless so they can scale horizontally. Downloads are served via short-lived
    pre-signed URLs (`S3_PRESIGNED_URL_EXPIRE_SECONDS`) that force `Content-Disposition: attachment`,
    so file bytes never pass through the API. boto3 is synchronous, so calls run in a worker thread.
    Use a private bucket with server-side encryption and block public access.
    """

    def __init__(self) -> None:
        secret = config.S3_SECRET_ACCESS_KEY.get_secret_value() if config.S3_SECRET_ACCESS_KEY else None
        self.bucket = config.S3_BUCKET
        self._client: Any = boto3.client(
            "s3",
            endpoint_url=config.S3_ENDPOINT_URL or None,
            region_name=config.S3_REGION,
            aws_access_key_id=config.S3_ACCESS_KEY_ID or None,
            aws_secret_access_key=secret,
            config=BotoConfig(signature_version="s3v4", retries={"max_attempts": 3, "mode": "standard"}),
        )

    async def save(self, source: BinaryIO, owner_id: uuid.UUID, extension: str, max_bytes: int) -> tuple[str, int]:
        key = new_storage_key(owner_id, extension)
        reader = _LimitedReader(source, max_bytes)
        # upload_fileobj aborts the multipart upload if the reader raises (e.g. size limit).
        await run_in_threadpool(self._client.upload_fileobj, reader, self.bucket, key)
        return key, reader.size

    async def exists(self, key: str) -> bool:
        try:
            await run_in_threadpool(self._client.head_object, Bucket=self.bucket, Key=key)
        except ClientError as e:
            if e.response.get("Error", {}).get("Code") in {"404", "NoSuchKey", "NotFound"}:
                return False
            raise
        return True

    async def delete(self, key: str) -> None:
        await run_in_threadpool(self._client.delete_object, Bucket=self.bucket, Key=key)

    async def delete_owner(self, owner_id: uuid.UUID) -> None:
        def _delete_prefix() -> None:
            paginator = self._client.get_paginator("list_objects_v2")
            for page in paginator.paginate(Bucket=self.bucket, Prefix=f"{owner_id}/"):
                objects = [{"Key": obj["Key"]} for obj in page.get("Contents", [])]
                if objects:
                    self._client.delete_objects(Bucket=self.bucket, Delete={"Objects": objects, "Quiet": True})

        await run_in_threadpool(_delete_prefix)

    async def download_url(self, key: str, filename: str, media_type: str) -> str | None:
        url: str = await run_in_threadpool(
            self._client.generate_presigned_url,
            "get_object",
            Params={
                "Bucket": self.bucket,
                "Key": key,
                "ResponseContentDisposition": f"attachment; filename*=UTF-8''{quote(filename)}",
                "ResponseContentType": media_type,
            },
            ExpiresIn=config.S3_PRESIGNED_URL_EXPIRE_SECONDS,
        )
        return url

    def path(self, key: str) -> Path:
        raise NotImplementedError("S3 storage serves downloads via pre-signed URLs")
