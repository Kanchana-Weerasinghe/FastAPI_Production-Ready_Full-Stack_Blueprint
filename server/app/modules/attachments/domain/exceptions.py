"""Framework-independent attachment domain violations."""


class AttachmentRuleViolation(ValueError):
    """A filename or attachment invariant was violated."""

    def __init__(self, code: str, message: str) -> None:
        self.code = code
        super().__init__(message)
