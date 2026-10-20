from unittest.mock import AsyncMock


class FakeAuditService:
    """Records audit calls in memory for unit tests."""

    def __init__(self) -> None:
        self.record = AsyncMock()
