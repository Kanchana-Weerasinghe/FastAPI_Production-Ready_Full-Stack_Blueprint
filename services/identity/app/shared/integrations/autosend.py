from app.core.config import config
from app.core.logging import logger
from app.shared.http import ResilientHttpClient


class AutosendClient:
    """
    Email transport backed by the Autosend HTTP API.

    Calls go through `ResilientHttpClient` (timeouts, retries with backoff, circuit breaker). Delivery
    is normally driven by the outbox worker, which retries failed events; this client returns False
    instead of raising so the worker can record the failure.
    """

    def __init__(self) -> None:
        self.http = ResilientHttpClient(
            "autosend",
            base_url=config.AUTOSEND_URL,
            headers={
                "Authorization": f"Bearer {config.AUTOSEND_API_KEY.get_secret_value()}",
                "Content-Type": "application/json",
            },
        )

    async def send_email(self, to: str, subject: str, html: str, name: str | None = None) -> bool:
        """Sends one transactional email. Returns False (and logs) instead of raising on failure."""
        payload = {
            "to": {"email": to, "name": name or to},
            "from": {"email": config.AUTOSEND_FROM_EMAIL, "name": config.AUTOSEND_FROM_NAME},
            "subject": subject,
            "html": html,
        }
        try:
            # The outbox already makes delivery at-least-once, so retrying the POST here is acceptable.
            response = await self.http.post("", json=payload, retry_non_idempotent=True)
            if response.status_code == 200 and response.json().get("success"):
                logger.info("autosend_email_sent_successfully", subject=subject)
                return True
            logger.error("autosend_email_send_failed", status=response.status_code, body=response.text[:500])
        except Exception as e:
            logger.exception("autosend_email_send_exception", error=str(e))
        return False

    async def aclose(self) -> None:
        await self.http.aclose()
