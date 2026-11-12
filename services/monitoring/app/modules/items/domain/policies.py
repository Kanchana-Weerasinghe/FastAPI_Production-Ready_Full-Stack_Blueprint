"""
POLICIES: EVERY business rule of the items module, in one file.

A policy is a CHECK: it answers "is this allowed?" and raises a domain error if not.
    - It never changes anything (changes are entity methods).
    - It never touches the database: a fact it needs (e.g. "is this code taken?") is passed in.

Who calls them: the entity methods (entities.py), as their first line. So every change of a
item is checked, and a rule cannot be skipped.

    ensure_can_archive(item)             -> raises if it is already archived
    ensure_code_is_free(code, taken=True)      -> raises ItemCodeTaken
"""

from typing import TYPE_CHECKING

from app.modules.items.domain.exceptions import InvalidItemState, ItemCodeTaken
from app.modules.items.domain.value_objects import ItemCode, ItemStatus

if TYPE_CHECKING:  # type hints only: entities.py imports this file, so no runtime import back
    from app.modules.items.domain.entities import Item


def ensure_code_is_free(code: ItemCode, *, taken: bool) -> None:
    """The code must be unique. The use case asks the repository and passes `taken`."""
    if taken:
        raise ItemCodeTaken(f"Code {code.value} is already used")


def ensure_is_active(item: "Item", *, action: str) -> None:
    """An archived item cannot be changed (restore it first)."""
    if item.status is not ItemStatus.ACTIVE:
        raise InvalidItemState(f"Cannot {action} an archived item; restore it first")


def ensure_can_archive(item: "Item") -> None:
    """A item cannot be archived twice."""
    if item.status is ItemStatus.ARCHIVED:
        raise InvalidItemState("The item is already archived")


def ensure_can_restore(item: "Item") -> None:
    """Only an archived item can be restored."""
    if item.status is not ItemStatus.ARCHIVED:
        raise InvalidItemState("Only an archived item can be restored")


def ensure_can_delete(item: "Item") -> None:
    """Only an archived item can be deleted (archive it first)."""
    if item.status is not ItemStatus.ARCHIVED:
        raise InvalidItemState("Archive the item before deleting it")
