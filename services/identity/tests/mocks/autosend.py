from unittest.mock import AsyncMock


class MockAutosendClient:
    """Mock email client to simulate email sending without external API calls."""

    def __init__(self) -> None:
        self.send_email = AsyncMock(return_value=True)
        self.aclose = AsyncMock()
