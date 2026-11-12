"""
DOMAIN ERRORS: one class per business rule that can be broken.

Each error has a stable `code` (clients rely on it: never rename it) and an HTTP status taken from the
class it extends:
    UnprocessableError -> 422  invalid input            (raised by value objects)
    ConflictError      -> 409  the action breaks a rule (raised by a policy)
    NotFoundError      -> 404  no such record           (raised by the repository)

The API turns them into problem responses automatically, e.g.
    {"status": 409, "code": "invalid_item_state", "detail": "Archive the item before deleting it", ...}

The domain imports only `platform_kit.errors` (no FastAPI, no `app.core`).
"""

from platform_kit.errors import ConflictError, NotFoundError, UnprocessableError


class InvalidItemName(UnprocessableError):
    """The name is not 3-120 characters long."""

    code = "invalid_item_name"


class InvalidItemCode(UnprocessableError):
    """The code is not 2-20 letters, digits or dashes."""

    code = "invalid_item_code"


class ItemCodeTaken(ConflictError):
    """Another item already uses this code (raised by the policy)."""

    code = "item_code_taken"


class InvalidItemState(ConflictError):
    """The action is not allowed in the current status, e.g. renaming an archived item (raised by the entity)."""

    code = "invalid_item_state"


class ItemNotFound(NotFoundError):
    """No item with this id (raised by the repository)."""

    code = "item_not_found"

    def __init__(self) -> None:
        super().__init__("Item not found")
