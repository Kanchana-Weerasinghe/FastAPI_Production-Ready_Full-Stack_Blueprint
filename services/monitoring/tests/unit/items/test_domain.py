"""
DOMAIN TESTS: the rules on their own. Fast: no database, no HTTP.

    Value objects -> format checks on one value
    Policies      -> every business rule, tested directly
    Entity        -> each method runs its rule, changes the data and records its event
"""

from datetime import UTC, datetime

import pytest

from app.modules.items.domain.entities import Item
from app.modules.items.domain.exceptions import (
    InvalidItemCode,
    InvalidItemName,
    InvalidItemState,
    ItemCodeTaken,
)
from app.modules.items.domain.policies import (
    ensure_can_archive,
    ensure_can_delete,
    ensure_can_restore,
    ensure_code_is_free,
    ensure_is_active,
)
from app.modules.items.domain.value_objects import NAME_MAX_LENGTH, ItemCode, ItemName, ItemStatus

NOW = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)


def _new() -> Item:
    return Item.create(name=ItemName("Blue pen"), code=ItemCode("ITM-001"), code_taken=False, at=NOW)


def _archived() -> Item:
    item = _new()
    item.archive(at=NOW)
    return item


# --- Value objects: format checks ------------------------------------------------------------------


def test_name_removes_extra_spaces() -> None:
    assert ItemName("  Blue   pen ").value == "Blue pen"


@pytest.mark.parametrize("raw", ["ab", "   ", "x" * (NAME_MAX_LENGTH + 1)])
def test_name_must_be_3_to_120_characters(raw: str) -> None:
    with pytest.raises(InvalidItemName):
        ItemName(raw)


def test_code_is_trimmed_and_upper_case() -> None:
    assert ItemCode(" itm-001 ").value == "ITM-001"


@pytest.mark.parametrize("raw", ["A", "ITM 001", "-ITM", "ITM_001", "X" * 21])
def test_code_must_be_2_to_20_letters_digits_or_dashes(raw: str) -> None:
    with pytest.raises(InvalidItemCode):
        ItemCode(raw)


# --- Policies: every business rule, on its own -----------------------------------------------------


def test_policy_code_must_be_free() -> None:
    ensure_code_is_free(ItemCode("ITM-001"), taken=False)
    with pytest.raises(ItemCodeTaken):
        ensure_code_is_free(ItemCode("ITM-001"), taken=True)


def test_policy_only_an_active_item_can_change() -> None:
    ensure_is_active(_new(), action="rename")
    with pytest.raises(InvalidItemState):
        ensure_is_active(_archived(), action="rename")


def test_policy_cannot_archive_twice() -> None:
    ensure_can_archive(_new())
    with pytest.raises(InvalidItemState):
        ensure_can_archive(_archived())


def test_policy_only_an_archived_item_can_be_restored() -> None:
    ensure_can_restore(_archived())
    with pytest.raises(InvalidItemState):
        ensure_can_restore(_new())


def test_policy_only_an_archived_item_can_be_deleted() -> None:
    ensure_can_delete(_archived())
    with pytest.raises(InvalidItemState):
        ensure_can_delete(_new())


# --- Entity: each method = rule -> change -> event -------------------------------------------------


def test_create_makes_an_active_item_and_records_created() -> None:
    item = _new()
    assert item.status is ItemStatus.ACTIVE
    assert [e.name for e in item.pull_events()] == ["ItemCreated"]
    assert item.pull_events() == []  # pulled events are cleared


def test_create_runs_the_unique_code_rule() -> None:
    with pytest.raises(ItemCodeTaken):
        Item.create(name=ItemName("Blue pen"), code=ItemCode("ITM-001"), code_taken=True, at=NOW)


def test_archive_changes_the_status_and_records_archived() -> None:
    item = _archived()
    assert item.status is ItemStatus.ARCHIVED
    assert [e.name for e in item.pull_events()] == ["ItemCreated", "ItemArchived"]


def test_restore_makes_it_active_again() -> None:
    item = _archived()
    item.restore(at=NOW)
    assert item.status is ItemStatus.ACTIVE


def test_methods_refuse_what_the_rules_refuse() -> None:
    archived = _archived()
    with pytest.raises(InvalidItemState):
        archived.rename(ItemName("Red pen"), at=NOW)
    with pytest.raises(InvalidItemState):
        archived.change_code(ItemCode("ITM-002"), code_taken=False, at=NOW)
    with pytest.raises(InvalidItemState):
        _new().delete()
    with pytest.raises(ItemCodeTaken):
        _new().change_code(ItemCode("ITM-002"), code_taken=True, at=NOW)
