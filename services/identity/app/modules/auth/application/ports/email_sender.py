"""Email delivery contract consumed by authentication workflows."""

from typing import Protocol


class EmailSender(Protocol):
    """Outbound email port; adapters enqueue or deliver through a selected provider."""

    async def send_email(self, to: str, subject: str, html: str, name: str | None = None) -> bool: ...
