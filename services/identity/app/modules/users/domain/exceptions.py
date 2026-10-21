"""
Named business errors of the users domain.

Plain Python (the domain may not import `app.core`). Each error carries a stable `code`; the
application layer (`UserUseCases`) translates them into `BadRequestError`, which the HTTP handlers
render as RFC 9457 responses.
"""


class UserRuleViolation(Exception):
    """Base class: a request would break a rule of the user account."""

    code = "user_rule_violation"

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


class InvalidEmailAddress(UserRuleViolation):
    code = "invalid_email"


class InvalidUsername(UserRuleViolation):
    code = "invalid_username"


class InvalidPasswordHash(UserRuleViolation):
    code = "invalid_password_hash"


class InvalidRole(UserRuleViolation):
    code = "invalid_role"


class MfaAlreadyEnabled(UserRuleViolation):
    code = "mfa_already_enabled"


class MfaNotStarted(UserRuleViolation):
    code = "mfa_not_started"
