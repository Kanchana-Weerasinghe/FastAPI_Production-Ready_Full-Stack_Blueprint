from typing import Annotated

from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, Request, Response, status

from app.core.client_ip import get_real_ip_address
from app.core.config import config
from app.core.security import clear_auth_cookies, rate_limit, set_auth_cookies
from app.modules.auth.application.contracts import ClientInfo, SessionTokens
from app.modules.auth.dependencies import CurrentUserDep
from app.modules.auth.public import AuthService
from app.modules.auth.schemas import (
    EmailRequest,
    MfaCode,
    MfaSetupResponse,
    MfaVerify,
    PasswordChange,
    PasswordReset,
    SignIn,
    SignInResponse,
    SignUp,
    TokenRequest,
)

router = APIRouter(prefix="/auth", tags=["auth"])

AuthServiceDep = Annotated[AuthService, Depends(Provide["auth.service"])]


def _client(request: Request) -> ClientInfo:
    return ClientInfo(ip_address=get_real_ip_address(request), user_agent=request.headers.get("user-agent"))


ClientDep = Annotated[ClientInfo, Depends(_client)]


def _start_session(response: Response, tokens: SessionTokens) -> None:
    set_auth_cookies(
        response,
        access_token=tokens.access_token,
        refresh_token=tokens.refresh_token,
        csrf_token=tokens.csrf_token,
    )


@router.post(
    "/signup", status_code=status.HTTP_201_CREATED, summary="User Signup", dependencies=[rate_limit("5/minute")]
)
@inject
async def signup(user_info: SignUp, service: AuthServiceDep) -> None:
    """Registers a new user account and emails a verification link."""
    await service.sign_up(user_info.email, user_info.password)


@router.post("/signin", response_model=SignInResponse, summary="User Signin", dependencies=[rate_limit("10/minute")])
@inject
async def signin(response: Response, credentials: SignIn, client: ClientDep, service: AuthServiceDep) -> SignInResponse:
    """Verifies credentials and starts a session, or returns an MFA challenge when TOTP is enabled."""
    result, tokens = await service.sign_in(credentials.email, credentials.password, client)
    if tokens is not None:
        _start_session(response, tokens)
    return SignInResponse(mfa_required=result.mfa_required, mfa_token=result.mfa_token)


@router.post(
    "/mfa/verify",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Complete MFA Signin",
    dependencies=[rate_limit("10/minute")],
)
@inject
async def mfa_verify(response: Response, data: MfaVerify, client: ClientDep, service: AuthServiceDep) -> None:
    """Exchanges an MFA challenge token and a TOTP code for a session."""
    _start_session(response, await service.verify_mfa(data.mfa_token, data.code, client))


@router.post(
    "/refresh",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Refresh Session",
    dependencies=[rate_limit("30/minute")],
)
@inject
async def refresh(request: Request, response: Response, client: ClientDep, service: AuthServiceDep) -> None:
    """Rotates the refresh token cookie and issues a new access token."""
    tokens = await service.refresh(request.cookies.get(config.REFRESH_COOKIE_NAME), client)
    _start_session(response, tokens)


@router.post(
    "/signout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="User Signout",
    dependencies=[rate_limit("30/minute")],
)
@inject
async def signout(request: Request, response: Response, service: AuthServiceDep) -> None:
    """Revokes the current session and clears the session cookies. Idempotent."""
    await service.sign_out(request.cookies.get(config.REFRESH_COOKIE_NAME))
    clear_auth_cookies(response)


@router.post(
    "/signout-all",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Sign Out Everywhere",
    dependencies=[rate_limit("10/minute")],
)
@inject
async def signout_all(response: Response, current_user: CurrentUserDep, service: AuthServiceDep) -> None:
    """Revokes every session of the current user on every device."""
    await service.sign_out_everywhere(current_user)
    clear_auth_cookies(response)


@router.post(
    "/verify-email",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Verify Email",
    dependencies=[rate_limit("10/minute")],
)
@inject
async def verify_email(data: TokenRequest, service: AuthServiceDep) -> None:
    """Confirms the email address using the single-use token from the verification email."""
    await service.verify_email(data.token)


@router.post(
    "/verify-email/resend",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Resend Verification Email",
    dependencies=[rate_limit("3/minute")],
)
@inject
async def resend_verification(current_user: CurrentUserDep, service: AuthServiceDep) -> None:
    """Sends a new verification link (previous links stop working)."""
    await service.resend_verification(current_user)


@router.post(
    "/password/forgot",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Request Password Reset",
    dependencies=[rate_limit("3/minute")],
)
@inject
async def forgot_password(data: EmailRequest, service: AuthServiceDep) -> None:
    """Emails a single-use reset link if the account exists. Always returns 202."""
    await service.forgot_password(data.email)


@router.post(
    "/password/reset",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Reset Password",
    dependencies=[rate_limit("5/minute")],
)
@inject
async def reset_password(response: Response, data: PasswordReset, service: AuthServiceDep) -> None:
    """Sets a new password using a reset token; signs the user out everywhere."""
    await service.reset_password(data.token, data.new_password)
    clear_auth_cookies(response)


@router.post(
    "/password/change",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Change Password",
    dependencies=[rate_limit("5/minute")],
)
@inject
async def change_password(
    response: Response, data: PasswordChange, client: ClientDep, current_user: CurrentUserDep, service: AuthServiceDep
) -> None:
    """Changes the password, signs out all other sessions and refreshes this one."""
    tokens = await service.change_password(current_user, data.current_password, data.new_password, client)
    _start_session(response, tokens)


@router.post(
    "/mfa/setup", response_model=MfaSetupResponse, summary="Start MFA Setup", dependencies=[rate_limit("5/minute")]
)
@inject
async def mfa_setup(current_user: CurrentUserDep, service: AuthServiceDep) -> MfaSetupResponse:
    """Generates a TOTP secret to add to an authenticator app; confirm it with /mfa/enable."""
    result = await service.start_mfa_setup(current_user)
    return MfaSetupResponse(secret=result.secret, otpauth_uri=result.otpauth_uri)


@router.post(
    "/mfa/enable",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Enable MFA",
    dependencies=[rate_limit("10/minute")],
)
@inject
async def mfa_enable(data: MfaCode, current_user: CurrentUserDep, service: AuthServiceDep) -> None:
    """Activates MFA after verifying a code from the authenticator app."""
    await service.confirm_mfa_setup(current_user, data.code)


@router.post(
    "/mfa/disable",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Disable MFA",
    dependencies=[rate_limit("10/minute")],
)
@inject
async def mfa_disable(data: MfaCode, current_user: CurrentUserDep, service: AuthServiceDep) -> None:
    """Turns MFA off; requires a current authenticator code."""
    await service.disable_mfa(current_user, data.code)
