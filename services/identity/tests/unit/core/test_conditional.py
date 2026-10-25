import pytest
from fastapi import Response

from app.core.conditional import check_if_match, etag_for, set_etag
from app.core.errors import BadRequestError, PreconditionFailedError


def test_etag_is_a_weak_tag_of_the_version() -> None:
    """Verify the ETag of version 3 is W/"3" and set_etag writes it to the response."""
    response = Response()
    set_etag(response, 3)
    assert etag_for(3) == 'W/"3"'
    assert response.headers["etag"] == 'W/"3"'


@pytest.mark.parametrize("if_match", [None, "*", 'W/"3"', '"3"', 'W/"1", W/"3"'])
def test_matching_or_absent_if_match_passes(if_match: str | None) -> None:
    """Verify a missing, wildcard or matching If-Match lets the write through."""
    check_if_match(if_match, current_version=3)


def test_stale_if_match_fails_with_the_current_etag() -> None:
    """Verify a stale If-Match raises 412 precondition_failed and reports the current ETag."""
    with pytest.raises(PreconditionFailedError) as error:
        check_if_match('W/"2"', current_version=3)
    assert error.value.code == "precondition_failed"
    assert error.value.extra == {"current_etag": 'W/"3"'}


def test_malformed_if_match_is_rejected() -> None:
    """Verify an If-Match that is not an ETag raises 400 invalid_if_match."""
    with pytest.raises(BadRequestError) as error:
        check_if_match("version-3", current_version=3)
    assert error.value.code == "invalid_if_match"
