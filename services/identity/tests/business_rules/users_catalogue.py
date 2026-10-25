"""
Test-case catalogue for the UserAccount business rules: the specification the code is built from.

Test-driven workflow: write the business rules and their test cases here first, then one pytest
test per case (tagged `@pytest.mark.br("BR-xx", "TC-xx-y")`), then the code that makes them pass.
`test_traceability.py` fails the run if a rule or case has no test, or a test names an unknown one.

Layers: domain (no database), use_case (fake ports, no database), repository (adapter against the
real database), api (real HTTP + database).
"""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class TestCase:
    id: str
    layer: str  # domain | use_case | repository | api
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
            TestCase(
                "TC-01-6",
                "repository",
                "an account stored in the database",
                "it is loaded through the repository",
                "every field round-trips and email/username/password/role come back as value objects",
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
            TestCase(
                "TC-03-6",
                "repository",
                "a stored row whose password is not a bcrypt hash",
                "it is loaded through the repository",
                "InvalidPasswordHash: invalid data never reaches the use cases",
            ),
            TestCase(
                "TC-03-7",
                "repository",
                "an account loaded once",
                "increment_token_version runs twice",
                "the database returns 1 then 2 (counted in SQL, not from the loaded copy)",
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
            TestCase(
                "TC-04-3",
                "repository",
                "a stored row with an unknown role",
                "it is loaded through the repository",
                "InvalidRole: invalid data never reaches the use cases",
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
            TestCase(
                "TC-05-2",
                "repository",
                "a sign-up that passed the existence check at the same moment as another",
                "create_account inserts the same email",
                "ConflictError (409) from the unique constraint; still one account",
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
            TestCase(
                "TC-06-3",
                "api",
                "a new account and its verification link",
                "POST /v1/auth/verify-email twice",
                "204 and emailVerified true; the second use is rejected (invalid_or_expired_token)",
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
            TestCase(
                "TC-07-6",
                "api",
                "a signed-in user without MFA setup",
                "POST /v1/auth/mfa/enable",
                "400 mfa_not_started",
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
            TestCase(
                "TC-08-7",
                "repository",
                "an account loaded once (stale copy)",
                "register_failed_login runs 3 times",
                "the database counts 3: concurrent failures are never lost",
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
            TestCase(
                "TC-09-4",
                "api",
                "an account whose lock has expired",
                "sign-in with the correct password",
                "200 and the lock is cleared in the database",
            ),
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
            TestCase(
                "TC-10-3",
                "api",
                "a user with a todo and a stored file",
                "DELETE /v2/user/me",
                "user.deleted is audited, the todo is gone (cascade) and the file is removed",
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
            TestCase(
                "TC-11-5",
                "api",
                "a signed-in admin",
                "GET /v2/users/?pageSize=1",
                "one user per page, with createdAt and lockedUntil, and the total count",
            ),
        ),
    ),
    BusinessRule(
        "BR-12",
        "An inactive (deactivated) account cannot sign in or use an existing session.",
        (
            TestCase(
                "TC-12-1",
                "api",
                "a deactivated account",
                "sign-in with the correct password",
                "401 account_inactive; a wrong password still answers invalid_credentials",
            ),
            TestCase(
                "TC-12-2", "api", "a session created before the account was deactivated", "GET /v2/user/me", "401"
            ),
        ),
    ),
)
