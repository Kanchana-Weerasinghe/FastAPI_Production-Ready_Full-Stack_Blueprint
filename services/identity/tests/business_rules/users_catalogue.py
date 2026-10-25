"""
Test-case catalogue for the UserAccount business rules: the specification the code is built from.

Test-driven workflow: write the business rules and their test cases here first, then one pytest
test per case (tagged `@pytest.mark.br("BR-xx", "TC-xx-y")`), then the code that makes them pass.
`test_traceability.py` fails the run if a rule or case has no test, or a test names an unknown one.

Layers: domain (no database), use_case (fake ports, no database), api (real HTTP + database).
"""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class TestCase:
    id: str
    layer: str  # domain | use_case | api
    given: str
    when: str
    then: str


@dataclass(frozen=True, slots=True)
class BusinessRule:
    id: str
    rule: str
    cases: tuple[TestCase, ...]


USER_RULES: tuple[BusinessRule, ...] = (
    BusinessRule(
        "BR-01",
        "Every user has an email address that must be a valid address.",
        (
            TestCase(
                "TC-01-1",
                "domain",
                "a valid email with spaces around it",
                "EmailAddress is created",
                "it is accepted and trimmed",
            ),
            TestCase(
                "TC-01-2",
                "domain",
                "malformed or over-long emails",
                "EmailAddress is created",
                "InvalidEmailAddress (invalid_email)",
            ),
            TestCase(
                "TC-01-3",
                "domain",
                "an account built with an invalid email",
                "UserAccount is created",
                "InvalidEmailAddress: the entity can never hold it",
            ),
            TestCase(
                "TC-01-4",
                "use_case",
                "an invalid email",
                "create_user runs",
                "BadRequestError invalid_email and nothing is stored",
            ),
            TestCase(
                "TC-01-5",
                "api",
                "a sign-up request with an invalid email",
                "POST /v1/auth/signup",
                "422 validation_failed",
            ),
        ),
    ),
    BusinessRule(
        "BR-02",
        "A username is 3-50 letters, digits, dots, underscores or hyphens.",
        (
            TestCase(
                "TC-02-1",
                "domain",
                "a handle with allowed characters",
                "Username is created",
                "it is accepted and trimmed",
            ),
            TestCase(
                "TC-02-2",
                "domain",
                "too short, too long or with spaces/@",
                "Username is created",
                "InvalidUsername (invalid_username)",
            ),
            TestCase(
                "TC-02-3",
                "use_case",
                "an invalid username",
                "create_user runs",
                "BadRequestError invalid_username and nothing is stored",
            ),
        ),
    ),
    BusinessRule(
        "BR-03",
        "Only a password hash is ever stored, never the plain password.",
        (
            TestCase("TC-03-1", "domain", "a bcrypt hash", "PasswordHash is created", "it is accepted"),
            TestCase(
                "TC-03-2",
                "domain",
                "a plain password or malformed hash",
                "PasswordHash is created",
                "InvalidPasswordHash",
            ),
            TestCase(
                "TC-03-3",
                "domain",
                "an account",
                "change_password gets a plain password",
                "rejected; the old hash is kept",
            ),
            TestCase(
                "TC-03-4",
                "use_case",
                "a plain password",
                "set_password runs",
                "BadRequestError invalid_password_hash; nothing saved; sessions not revoked",
            ),
            TestCase(
                "TC-03-5",
                "use_case",
                "a new bcrypt hash",
                "set_password runs",
                "hash saved and every access token revoked (token_version + 1)",
            ),
        ),
    ),
    BusinessRule(
        "BR-04",
        "A user's role is either user or admin.",
        (
            TestCase("TC-04-1", "domain", "the texts 'user' and 'admin'", "Role.parse runs", "Role.USER / Role.ADMIN"),
            TestCase(
                "TC-04-2",
                "domain",
                "an unknown role",
                "Role.parse runs / an account is built",
                "InvalidRole (invalid_role)",
            ),
        ),
    ),
    BusinessRule(
        "BR-05",
        "An email must be unique across all users.",
        (
            TestCase(
                "TC-05-1",
                "api",
                "an already registered email",
                "POST /v1/auth/signup with a new password",
                "201 like a new sign-up, no email sent, the old password still works and the new one does not",
            ),
        ),
    ),
    BusinessRule(
        "BR-06",
        "Verifying an email twice keeps the first verification date.",
        (
            TestCase(
                "TC-06-1",
                "domain",
                "an unverified account",
                "verify_email runs twice",
                "first returns True and sets the date; second returns False and keeps it",
            ),
            TestCase(
                "TC-06-2",
                "use_case",
                "an unverified account",
                "mark_email_verified runs twice",
                "the date is saved once",
            ),
        ),
    ),
    BusinessRule(
        "BR-07",
        "MFA must be set up before it can be enabled, and cannot be set up again while enabled.",
        (
            TestCase("TC-07-1", "domain", "an account without MFA", "enable_mfa runs", "MfaNotStarted"),
            TestCase(
                "TC-07-2",
                "domain",
                "an account without MFA",
                "start_mfa_setup then enable_mfa",
                "MFA enabled at the given time",
            ),
            TestCase("TC-07-3", "domain", "an account with MFA enabled", "start_mfa_setup runs", "MfaAlreadyEnabled"),
            TestCase(
                "TC-07-4",
                "domain",
                "an account with MFA enabled",
                "disable_mfa runs",
                "secret and activation are cleared",
            ),
            TestCase(
                "TC-07-5",
                "use_case",
                "an account without MFA",
                "set_mfa_secret(enabled=True)",
                "BadRequestError mfa_not_started; nothing saved",
            ),
        ),
    ),
    BusinessRule(
        "BR-08",
        "After 5 failed sign-ins the account is locked for a configurable 15 minutes.",
        (
            TestCase(
                "TC-08-1",
                "domain",
                "a lock time and a lockout duration",
                "lockout_expiry runs",
                "expiry = lock time + duration",
            ),
            TestCase("TC-08-2", "domain", "a clock without a timezone", "lockout_expiry runs", "ValueError"),
            TestCase(
                "TC-08-3",
                "use_case",
                "an account with 3 failures",
                "record_failed_login runs",
                "4 failures, not locked; failure kept although the response fails",
            ),
            TestCase(
                "TC-08-4",
                "use_case",
                "an account with 4 failures",
                "record_failed_login runs",
                "locked for LOGIN_LOCKOUT_MINUTES and the counter restarts",
            ),
            TestCase(
                "TC-08-5",
                "use_case",
                "a locked account / an account without failures",
                "reset_failed_logins runs",
                "counter and lock cleared and saved / nothing saved",
            ),
            TestCase(
                "TC-08-6",
                "api",
                "a registered user",
                "5 sign-ins with a wrong password",
                "the account is locked in the database",
            ),
        ),
    ),
    BusinessRule(
        "BR-09",
        "A locked user cannot sign in until the lock expires.",
        (
            TestCase(
                "TC-09-1",
                "domain",
                "lock expiry in the future / past / none",
                "is_locked(now) runs",
                "True / False / False",
            ),
            TestCase("TC-09-2", "domain", "a clock without a timezone", "is_locked runs", "ValueError"),
            TestCase("TC-09-3", "api", "a locked account", "sign-in with the correct password", "401 account_locked"),
        ),
    ),
    BusinessRule(
        "BR-10",
        "A user can delete their own account; their files are removed only after the deletion is saved.",
        (
            TestCase(
                "TC-10-1",
                "use_case",
                "an account",
                "delete_account runs",
                "account deleted and audited; file cleanup scheduled, not run before commit, run after commit",
            ),
            TestCase(
                "TC-10-2",
                "api",
                "a signed-in user",
                "DELETE /v2/user/me",
                "204, session cookies expired, then 401 on the next call",
            ),
        ),
    ),
    BusinessRule(
        "BR-11",
        "A signed-in user can view their own profile; only admins can list all users.",
        (
            TestCase("TC-11-1", "api", "a signed-in user", "GET /v2/user/me", "200 with own profile and no secrets"),
            TestCase("TC-11-2", "api", "no session", "GET /v2/user/me", "401"),
            TestCase("TC-11-3", "api", "a signed-in normal user", "GET /v2/users/", "403"),
            TestCase("TC-11-4", "api", "a signed-in admin", "GET /v2/users/", "200 with a page of users"),
        ),
    ),
)
