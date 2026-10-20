from typing import Protocol
from uuid import UUID


class Actor(Protocol):
    """
    The authenticated principal performing a use case.

    Modules depend on this protocol instead of importing the `users` module's ORM model,
    which keeps module boundaries clean (any object with `id` and `username` works,
    including test doubles).
    """

    @property
    def id(self) -> UUID: ...

    @property
    def username(self) -> str: ...
