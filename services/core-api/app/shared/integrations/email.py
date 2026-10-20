from typing import Any, Protocol

from app.shared.outbox import OutboxPublisher

EMAIL_SEND_EVENT = "email.send"


class EmailSender(Protocol):
    """
    Port for outbound email. Services depend on this protocol, never on a vendor client, so the
    provider (Autosend, SES, SendGrid, ...) can be swapped in the container without touching
    business code. Implementations return False (and log) instead of raising on delivery failure.
    """

    async def send_email(self, to: str, subject: str, html: str, name: str | None = None) -> bool: ...


class OutboxEmailSender:
    """
    The `EmailSender` services use: queues the email in the transactional outbox instead of calling
    the provider during the request. The email is only sent if the request commits, survives process
    crashes, and is retried by the worker if the provider fails.
    """

    def __init__(self, publisher: OutboxPublisher) -> None:
        self.publisher = publisher

    async def send_email(self, to: str, subject: str, html: str, name: str | None = None) -> bool:
        await self.publisher.publish(EMAIL_SEND_EVENT, {"to": to, "subject": subject, "html": html, "name": name})
        return True


class EmailDeliveryHandler:
    """Outbox handler for `email.send`: hands the email to the real transport; failure triggers a retry."""

    def __init__(self, transport: EmailSender) -> None:
        self.transport = transport

    async def __call__(self, payload: dict[str, Any]) -> None:
        if not await self.transport.send_email(payload["to"], payload["subject"], payload["html"], payload.get("name")):
            raise RuntimeError("Email provider did not accept the message")
