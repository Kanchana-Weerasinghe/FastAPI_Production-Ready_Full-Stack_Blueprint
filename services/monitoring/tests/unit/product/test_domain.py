"""
DOMAIN TESTS: the rules on their own. Fast: no database, no HTTP.

    Value objects -> format checks on one value
    Policies      -> every business rule, tested directly
    Entity        -> each method runs its rule, changes the data and records its event
"""

from datetime import UTC, datetime

import pytest

from app.modules.product.domain.entities import Product
from app.modules.product.domain.exceptions import (
    InvalidProductCode,
    InvalidProductName,
    InvalidProductState,
    ProductCodeTaken,
)
from app.modules.product.domain.policies import (
    ensure_can_archive,
    ensure_can_delete,
    ensure_can_restore,
    ensure_code_is_free,
    ensure_is_active,
)
from app.modules.product.domain.value_objects import NAME_MAX_LENGTH, ProductCode, ProductName, ProductStatus

NOW = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)


def _new() -> Product:
    return Product.create(name=ProductName("Blue pen"), code=ProductCode("ITM-001"), code_taken=False, at=NOW)


def _archived() -> Product:
    product = _new()
    product.archive(at=NOW)
    return product


# --- Value objects: format checks ------------------------------------------------------------------


def test_name_removes_extra_spaces() -> None:
    assert ProductName("  Blue   pen ").value == "Blue pen"


@pytest.mark.parametrize("raw", ["ab", "   ", "x" * (NAME_MAX_LENGTH + 1)])
def test_name_must_be_3_to_120_characters(raw: str) -> None:
    with pytest.raises(InvalidProductName):
        ProductName(raw)


def test_code_is_trimmed_and_upper_case() -> None:
    assert ProductCode(" itm-001 ").value == "ITM-001"


@pytest.mark.parametrize("raw", ["A", "ITM 001", "-ITM", "ITM_001", "X" * 21])
def test_code_must_be_2_to_20_letters_digits_or_dashes(raw: str) -> None:
    with pytest.raises(InvalidProductCode):
        ProductCode(raw)


# --- Policies: every business rule, on its own -----------------------------------------------------


def test_policy_code_must_be_free() -> None:
    ensure_code_is_free(ProductCode("ITM-001"), taken=False)
    with pytest.raises(ProductCodeTaken):
        ensure_code_is_free(ProductCode("ITM-001"), taken=True)


def test_policy_only_an_active_product_can_change() -> None:
    ensure_is_active(_new(), action="rename")
    with pytest.raises(InvalidProductState):
        ensure_is_active(_archived(), action="rename")


def test_policy_cannot_archive_twice() -> None:
    ensure_can_archive(_new())
    with pytest.raises(InvalidProductState):
        ensure_can_archive(_archived())


def test_policy_only_an_archived_product_can_be_restored() -> None:
    ensure_can_restore(_archived())
    with pytest.raises(InvalidProductState):
        ensure_can_restore(_new())


def test_policy_only_an_archived_product_can_be_deleted() -> None:
    ensure_can_delete(_archived())
    with pytest.raises(InvalidProductState):
        ensure_can_delete(_new())


# --- Entity: each method = rule -> change -> event -------------------------------------------------


def test_create_makes_an_active_product_and_records_created() -> None:
    product = _new()
    assert product.status is ProductStatus.ACTIVE
    assert [e.name for e in product.pull_events()] == ["ProductCreated"]
    assert product.pull_events() == []  # pulled events are cleared


def test_create_runs_the_unique_code_rule() -> None:
    with pytest.raises(ProductCodeTaken):
        Product.create(name=ProductName("Blue pen"), code=ProductCode("ITM-001"), code_taken=True, at=NOW)


def test_archive_changes_the_status_and_records_archived() -> None:
    product = _archived()
    assert product.status is ProductStatus.ARCHIVED
    assert [e.name for e in product.pull_events()] == ["ProductCreated", "ProductArchived"]


def test_restore_makes_it_active_again() -> None:
    product = _archived()
    product.restore(at=NOW)
    assert product.status is ProductStatus.ACTIVE


def test_methods_refuse_what_the_rules_refuse() -> None:
    archived = _archived()
    with pytest.raises(InvalidProductState):
        archived.rename(ProductName("Red pen"), at=NOW)
    with pytest.raises(InvalidProductState):
        archived.change_code(ProductCode("ITM-002"), code_taken=False, at=NOW)
    with pytest.raises(InvalidProductState):
        _new().delete()
    with pytest.raises(ProductCodeTaken):
        _new().change_code(ProductCode("ITM-002"), code_taken=True, at=NOW)
