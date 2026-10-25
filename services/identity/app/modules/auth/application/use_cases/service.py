import secrets
import string
import uuid
from datetime import UTC, datetime, timedelta

import pyotp

from app.core.config import config
from app.core.errors import AuthenticationError, BadRequestError
from app.core.logging import logger
from app.core.security import (
    create_access_token,
    create_mfa_challenge_token,
    decode_token,
    decrypt_field,
    encrypt_field,
    generate_opaque_token,
    hash_password_async,
    hash_token,
    verify_password_async,
)
from app.modules.audit.public import FAILURE, AuditService
from app.modules.auth import emails
from app.modules.auth.application.contracts import ClientInfo, MfaSetupDetails, SessionTokens, SignInOutcome
from app.modules.auth.application.ports.email_sender import EmailSender
from app.modules.auth.application.ports.token_repositories import (
    OneTimeTokenRepositoryPort,
    RefreshTokenRepositoryPort,
)
from app.modules.auth.domain.entities import OneTimeToken, RefreshToken
from app.modules.users.public import UserAccount, UserUseCases
from app.shared.unit_of_work import UnitOfWork

USERNAME_ALPHABET = string.ascii_uppercase + string.digits
PURPOSE_VERIFY_EMAIL = "verify_email"
PURPOSE_RESET_PASSWORD = "reset_password"
INVALID_CREDENTIALS = "Incorrect email or password"


def generate_username(length: int = 8) -> str:
    """Generates a random uppercase alphanumeric username using a CSPRNG."""
    return "".join(secrets.choice(USERNAME_ALPHABET) for _ in range(length))


class AuthService:
    """
    Authentication use cases: registration, sign-in (with lockout and optional TOTP MFA), session
    rotation and revocation, email verification and password reset/change.

    Accounts are owned by the users module; this service only talks to it through `UserUseCases`.
    """

    def __init__(
        self,
        user_use_cases: UserUseCases,
        refresh_tokens: RefreshTokenRepositoryPort,
        one_time_tokens: OneTimeTokenRepositoryPort,
        email_client: EmailSender,
        uow: UnitOfWork,
        audit: AuditService,
    ):
        self.audit = audit
        self.user_use_cases = user_use_cases
        self.refresh_tokens = refresh_tokens
        self.one_time_tokens = one_time_tokens
        self.email_client = email_client
        self.uow = uow

    # --- Registration & sign-in ---------------------------------------------------------------

    async def sign_up(self, email: str, password: str) -> None:
        """
        Registers a new account and queues welcome + verification emails (outbox, same transaction).

        Responds identically whether or not the email is taken, so sign-up can't be used to
        enumerate registered addresses.
        """
        logger.info("auth_sign_up_initiated")
        if await self.user_use_cases.get_by_email(email):
            logger.warning("auth_sign_up_failed_user_exists")
            return
        user = await self.user_use_cases.create_user(
            email=email,
            password_hash=await hash_password_async(password),
            username=generate_username(),
        )
        subject, html = emails.welcome_email(user.username)
        await self.email_client.send_email(user.email, subject, html, user.username)
        await self._send_verification(user)
        await self.audit.record("auth.signup", actor_id=user.id, resource_type="user", resource_id=user.id)

    async def sign_in(
        self, email: str, password: str, client: ClientInfo
    ) -> tuple[SignInOutcome, SessionTokens | None]:
        """
        Verifies credentials. Returns a session, or an MFA challenge when TOTP is enabled.

        Failed attempts are counted per account (in their own transaction) and lock the account
        for LOGIN_LOCKOUT_MINUTES after LOGIN_MAX_FAILED_ATTEMPTS failures.
        """
        user = await self.user_use_cases.get_by_email(email)
        if user is not None and self.user_use_cases.is_locked(user):
            logger.warning("auth_sign_in_locked", user_id=user.id)
            await self._audit_failure("auth.signin.locked", user.id)
            raise AuthenticationError("Too many failed attempts. Try again later.", code="account_locked")
        password_ok = await verify_password_async(password, user.password_hash if user else None)
        if user is None or not password_ok:
            if user is not None:
                await self.user_use_cases.record_failed_login(user)
            reason = "wrong_password" if user else "unknown_email"
            await self._audit_failure("auth.signin.failed", user.id if user else None, reason=reason)
            raise AuthenticationError(INVALID_CREDENTIALS, code="invalid_credentials")
        # Checked only after the password, so a wrong password reveals nothing about the account state.
        if not user.is_active:
            await self._audit_failure("auth.signin.inactive", user.id)
            raise AuthenticationError("This account is deactivated", code="account_inactive")
        await self.user_use_cases.reset_failed_logins(user)
        if config.REQUIRE_VERIFIED_EMAIL and user.email_verified_at is None:
            raise AuthenticationError("Verify your email address before signing in", code="email_not_verified")
        if user.mfa_enabled_at is not None:
            logger.info("auth_mfa_challenge_issued", user_id=user.id)
            return SignInOutcome(mfa_required=True, mfa_token=create_mfa_challenge_token(user.id)), None
        await self.audit.record("auth.signin.succeeded", actor_id=user.id)
        return SignInOutcome(), await self._create_session(user, client)

    async def verify_mfa(self, mfa_token: str, code: str, client: ClientInfo) -> SessionTokens:
        """Completes an MFA sign-in with a TOTP code."""
        claims = decode_token(mfa_token, "mfa_challenge")
        user = await self.user_use_cases.get_by_id(uuid.UUID(claims["sub"]))
        if not user.mfa_secret_encrypted or user.mfa_enabled_at is None or not self._totp_ok(user, code):
            await self.user_use_cases.record_failed_login(user)
            await self._audit_failure("auth.mfa.failed", user.id)
            raise AuthenticationError("Invalid authentication code", code="invalid_mfa_code")
        await self.audit.record("auth.signin.succeeded", actor_id=user.id, details={"mfa": True})
        return await self._create_session(user, client)

    # --- Sessions -------------------------------------------------------------------------------

    async def refresh(self, refresh_token: str | None, client: ClientInfo) -> SessionTokens:
        """
        Rotates a refresh token: the presented token is revoked and a new one issued in the same family.
        Presenting an already-revoked token signals theft, so the whole family is revoked.
        """
        if not refresh_token:
            raise AuthenticationError("Not authenticated", code="not_authenticated")
        stored = await self.refresh_tokens.get_by_hash(hash_token(refresh_token))
        if stored is None:
            raise AuthenticationError("Invalid refresh token", code="invalid_token")
        if stored.revoked_at is not None:
            logger.warning("refresh_token_reuse_detected", user_id=stored.user_id, family_id=stored.family_id)
            await self.refresh_tokens.revoke_family(stored.family_id)
            await self._audit_failure(
                "auth.refresh_token.reuse_detected", stored.user_id, family_id=str(stored.family_id)
            )
            raise AuthenticationError("Session has been revoked", code="refresh_token_reused")
        if stored.expires_at <= datetime.now(UTC):
            raise AuthenticationError("Session expired", code="token_expired")
        user = await self.user_use_cases.get_by_id(stored.user_id)
        tokens, new_token = await self._issue_session(user, client, family_id=stored.family_id)
        await self.refresh_tokens.rotate(stored.id, new_token.id, datetime.now(UTC))
        return tokens

    async def sign_out(self, refresh_token: str | None) -> None:
        """Revokes the current session (its refresh-token family). Idempotent."""
        if not refresh_token:
            return
        stored = await self.refresh_tokens.get_by_hash(hash_token(refresh_token))
        if stored is not None:
            await self.refresh_tokens.revoke_family(stored.family_id)

    async def sign_out_everywhere(self, user: UserAccount) -> None:
        """Revokes every session of the user: all refresh tokens and (via token_version) all access tokens."""
        await self.refresh_tokens.revoke_all_for_user(user.id)
        await self.user_use_cases.revoke_access_tokens(user)
        await self.audit.record("auth.signout_all", actor_id=user.id)
        logger.info("auth_signed_out_everywhere", user_id=user.id)

    # --- Email verification ---------------------------------------------------------------------

    async def resend_verification(self, user: UserAccount) -> None:
        if user.email_verified_at is None:
            await self._send_verification(user)

    async def verify_email(self, token: str) -> None:
        stored = await self._consume_one_time_token(token, PURPOSE_VERIFY_EMAIL)
        user = await self.user_use_cases.get_by_id(stored.user_id)
        await self.user_use_cases.mark_email_verified(user)
        await self.audit.record("auth.email.verified", actor_id=user.id)
        logger.info("auth_email_verified", user_id=user.id)

    # --- Passwords ------------------------------------------------------------------------------

    async def forgot_password(self, email: str) -> None:
        """Emails a single-use reset link. Always succeeds, so it can't be used to discover accounts."""
        user = await self.user_use_cases.get_by_email(email)
        if user is None:
            logger.info("auth_password_reset_unknown_email")
            return
        await self.one_time_tokens.invalidate_for_user(user.id, PURPOSE_RESET_PASSWORD)
        token = await self._create_one_time_token(
            user, PURPOSE_RESET_PASSWORD, timedelta(minutes=config.PASSWORD_RESET_EXPIRE_MINUTES)
        )
        subject, html = emails.password_reset_email(user.username, token)
        await self.email_client.send_email(user.email, subject, html, user.username)
        await self.audit.record("auth.password.reset_requested", actor_id=user.id)

    async def reset_password(self, token: str, new_password: str) -> None:
        """Sets a new password from a reset link and signs the user out everywhere."""
        stored = await self._consume_one_time_token(token, PURPOSE_RESET_PASSWORD)
        user = await self.user_use_cases.get_by_id(stored.user_id)
        await self._replace_password(user, new_password)
        await self.user_use_cases.reset_failed_logins(user)
        # Receiving the reset email proves control of the address.
        await self.user_use_cases.mark_email_verified(user)
        await self.audit.record("auth.password.reset", actor_id=user.id)

    async def change_password(
        self, user: UserAccount, current_password: str, new_password: str, client: ClientInfo
    ) -> SessionTokens:
        """Changes the password, revokes all other sessions and returns a new session for this device."""
        if not await verify_password_async(current_password, user.password_hash):
            raise AuthenticationError("Current password is incorrect", code="invalid_credentials")
        await self._replace_password(user, new_password)
        await self.audit.record("auth.password.changed", actor_id=user.id)
        return await self._create_session(user, client)

    # --- MFA (TOTP) -----------------------------------------------------------------------------

    async def start_mfa_setup(self, user: UserAccount) -> MfaSetupDetails:
        """Generates a new TOTP secret (stored encrypted, not yet active) for the user to scan."""
        if user.mfa_enabled_at is not None:
            raise BadRequestError("MFA is already enabled", code="mfa_already_enabled")
        secret = pyotp.random_base32()
        await self.user_use_cases.set_mfa_secret(user, encrypt_field(secret), enabled=False)
        uri = pyotp.TOTP(secret).provisioning_uri(name=user.email, issuer_name=config.PROJECT_NAME)
        return MfaSetupDetails(secret=secret, otpauth_uri=uri)

    async def confirm_mfa_setup(self, user: UserAccount, code: str) -> None:
        if user.mfa_secret_encrypted is None:
            raise BadRequestError("Start MFA setup first", code="mfa_not_started")
        if not self._totp_ok(user, code):
            raise BadRequestError("Invalid authentication code", code="invalid_mfa_code")
        await self.user_use_cases.set_mfa_secret(user, user.mfa_secret_encrypted, enabled=True)
        await self.audit.record("auth.mfa.enabled", actor_id=user.id)
        logger.info("auth_mfa_enabled", user_id=user.id)

    async def disable_mfa(self, user: UserAccount, code: str) -> None:
        if user.mfa_enabled_at is None or not self._totp_ok(user, code):
            raise BadRequestError("Invalid authentication code", code="invalid_mfa_code")
        await self.user_use_cases.set_mfa_secret(user, None, enabled=False)
        await self.audit.record("auth.mfa.disabled", actor_id=user.id)
        logger.info("auth_mfa_disabled", user_id=user.id)

    # --- Internals ------------------------------------------------------------------------------

    async def _audit_failure(self, action: str, actor_id: uuid.UUID | None, **details: str) -> None:
        """Records a failed security event and keeps it although the request then fails."""
        await self.audit.record(action, actor_id=actor_id, outcome=FAILURE, details=details)
        self.uow.persist_on_failure()

    @staticmethod
    def _totp_ok(user: UserAccount, code: str) -> bool:
        if not user.mfa_secret_encrypted:
            return False
        # valid_window=1 tolerates one 30-second step of clock drift.
        return pyotp.TOTP(decrypt_field(user.mfa_secret_encrypted)).verify(code, valid_window=1)

    async def _create_session(self, user: UserAccount, client: ClientInfo) -> SessionTokens:
        tokens, _ = await self._issue_session(user, client, family_id=uuid.uuid4())
        logger.info("auth_session_created", user_id=user.id)
        return tokens

    async def _issue_session(
        self, user: UserAccount, client: ClientInfo, *, family_id: uuid.UUID
    ) -> tuple[SessionTokens, RefreshToken]:
        refresh_token = generate_opaque_token()
        stored = await self.refresh_tokens.add(
            RefreshToken(
                id=uuid.uuid4(),
                user_id=user.id,
                token_hash=hash_token(refresh_token),
                family_id=family_id,
                expires_at=datetime.now(UTC) + timedelta(days=config.REFRESH_TOKEN_EXPIRE_DAYS),
                revoked_at=None,
                replaced_by_id=None,
                user_agent=(client.user_agent or "")[:500] or None,
                ip_address=client.ip_address,
                created_by=user.username,
                updated_by=user.username,
            )
        )
        access_token = create_access_token(user_id=user.id, role=user.role, token_version=user.token_version)
        return SessionTokens(
            access_token=access_token, refresh_token=refresh_token, csrf_token=generate_opaque_token()
        ), stored

    async def _replace_password(self, user: UserAccount, new_password: str) -> None:
        await self.user_use_cases.set_password(user, await hash_password_async(new_password))
        await self.refresh_tokens.revoke_all_for_user(user.id)
        await self.one_time_tokens.invalidate_for_user(user.id, PURPOSE_RESET_PASSWORD)
        subject, html = emails.password_changed_email(user.username)
        await self.email_client.send_email(user.email, subject, html, user.username)
        logger.info("auth_password_changed", user_id=user.id)

    async def _send_verification(self, user: UserAccount) -> None:
        await self.one_time_tokens.invalidate_for_user(user.id, PURPOSE_VERIFY_EMAIL)
        token = await self._create_one_time_token(
            user, PURPOSE_VERIFY_EMAIL, timedelta(hours=config.EMAIL_VERIFICATION_EXPIRE_HOURS)
        )
        subject, html = emails.verification_email(user.username, token)
        await self.email_client.send_email(user.email, subject, html, user.username)

    async def _create_one_time_token(self, user: UserAccount, purpose: str, ttl: timedelta) -> str:
        token = generate_opaque_token()
        await self.one_time_tokens.add(
            OneTimeToken(
                id=uuid.uuid4(),
                user_id=user.id,
                purpose=purpose,
                token_hash=hash_token(token),
                expires_at=datetime.now(UTC) + ttl,
                used_at=None,
                created_by=user.username,
                updated_by=user.username,
            )
        )
        return token

    async def _consume_one_time_token(self, token: str, purpose: str) -> OneTimeToken:
        stored = await self.one_time_tokens.get_usable(hash_token(token), purpose)
        if stored is None:
            raise BadRequestError("This link is invalid or has expired", code="invalid_or_expired_token")
        await self.one_time_tokens.mark_used(stored.id, datetime.now(UTC))
        return stored
