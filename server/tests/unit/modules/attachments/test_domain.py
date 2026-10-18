import pytest

from app.modules.attachments.domain.exceptions import AttachmentRuleViolation
from app.modules.attachments.domain.value_objects import UploadFileName


def test_upload_filename_uses_safe_basename_for_windows_paths() -> None:
    """Verify Windows-style client paths cannot become storage filenames."""
    value = UploadFileName.create(r"..\private\report.pdf", {".pdf"})

    assert value.value == "report.pdf"
    assert value.extension == ".pdf"


def test_upload_filename_rejects_unsupported_extensions() -> None:
    """Verify the domain value rejects a file type outside the configured allow-list."""
    with pytest.raises(AttachmentRuleViolation, match="File type not allowed"):
        UploadFileName.create("script.exe", {".pdf"})


def test_upload_filename_rejects_missing_names() -> None:
    """Verify an absent client filename is rejected as a domain violation."""
    with pytest.raises(AttachmentRuleViolation, match="File name is missing"):
        UploadFileName.create(None, {".pdf"})
