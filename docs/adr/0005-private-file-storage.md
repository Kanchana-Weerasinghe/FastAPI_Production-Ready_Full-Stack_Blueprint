# 0005. Private file storage behind authenticated downloads

- Status: Accepted
- Date: 2026-10-16

## Context

Uploads were written to `uploads/<user_id>/<client filename>` and served by a public `StaticFiles` mount, so anyone could download any file without authentication, client filenames could traverse paths or overwrite other uploads, there was no size limit, and disk I/O blocked the event loop.

## Decision

- Files live behind a storage interface (`app/shared/storage.py`, `LocalFileStorage`), never under a public mount. They are only served by the ownership-checked `GET /v2/attachments/{id}:download` endpoint, always as `Content-Disposition: attachment` with `X-Content-Type-Options: nosniff`.
- Storage keys are server-generated (`<owner_id>/<uuid><ext>`); the client filename is stored only as display metadata (base name only).
- Uploads are streamed with a size limit (`MAX_UPLOAD_SIZE_BYTES`); `MAX_REQUEST_BODY_BYTES` rejects oversized requests before multipart parsing, and the reverse proxy enforces the same limit.
- MIME type is derived from the extension, not trusted from the client.
- File deletion happens after commit (ADR 0004).

## Consequences

- Storage is a port (`FileStorage`) with two adapters selected by `STORAGE_BACKEND`: `local` (dev / single instance; makes the instance stateful) and `s3` (`S3FileStorage`, any S3-compatible service; required to scale horizontally).
- With `s3`, the download endpoint still performs the ownership check and then redirects (307) to a pre-signed URL valid for `S3_PRESIGNED_URL_EXPIRE_SECONDS`, so bytes never pass through the API. Use a private, encrypted, versioned bucket with public access blocked.
