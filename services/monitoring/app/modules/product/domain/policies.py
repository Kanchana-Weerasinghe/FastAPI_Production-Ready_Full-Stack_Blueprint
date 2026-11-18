"""
POLICIES: EVERY business rule of the product module, in one file.

A policy is a CHECK: it answers "is this allowed?" and raises a domain error if not.
    - It never changes anything (changes are entity methods).
    - It never touches the database: a fact it needs (e.g. "is this code taken?") is passed in.

Who calls them: the entity methods (entities.py), as their first line. So every change of a
product is checked, and a rule cannot be skipped.

    ensure_can_archive(product)             -> raises if it is already archived
    ensure_code_is_free(code, taken=True)      -> raises ProductCodeTaken
"""

from typing import TYPE_CHECKING

from app.modules.product.domain.exceptions import InvalidProductState, ProductCodeTaken
from app.modules.product.domain.value_objects import ProductCode, ProductStatus

if TYPE_CHECKING:  # type hints only: entities.py imports this file, so no runtime import back
    from app.modules.product.domain.entities import Product


def ensure_code_is_free(code: ProductCode, *, taken: bool) -> None:
    """The code must be unique. The use case asks the repository and passes `taken`."""
    if taken:
        raise ProductCodeTaken(f"Code {code.value} is already used")


def ensure_is_active(product: "Product", *, action: str) -> None:
    """An archived product cannot be changed (restore it first)."""
    if product.status is not ProductStatus.ACTIVE:
        raise InvalidProductState(f"Cannot {action} an archived product; restore it first")


def ensure_can_archive(product: "Product") -> None:
    """A product cannot be archived twice."""
    if product.status is ProductStatus.ARCHIVED:
        raise InvalidProductState("The product is already archived")


def ensure_can_restore(product: "Product") -> None:
    """Only an archived product can be restored."""
    if product.status is not ProductStatus.ARCHIVED:
        raise InvalidProductState("Only an archived product can be restored")


def ensure_can_delete(product: "Product") -> None:
    """Only an archived product can be deleted (archive it first)."""
    if product.status is not ProductStatus.ARCHIVED:
        raise InvalidProductState("Archive the product before deleting it")
