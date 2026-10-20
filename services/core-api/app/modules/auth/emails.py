"""Transactional email content for the auth module. Links point at the web app (FRONTEND_URL)."""

from html import escape
from urllib.parse import quote

from app.core.config import config


def _link(path: str, token: str) -> str:
    return f"{config.FRONTEND_URL.rstrip('/')}{path}?token={quote(token)}"


def welcome_email(username: str) -> tuple[str, str]:
    html = f"<h1>Welcome, {escape(username)}!</h1><p>Thanks for signing up to {escape(config.PROJECT_NAME)}.</p>"
    return f"Welcome to {config.PROJECT_NAME}!", html


def verification_email(username: str, token: str) -> tuple[str, str]:
    link = _link("/verify-email", token)
    hours = config.EMAIL_VERIFICATION_EXPIRE_HOURS
    html = (
        f"<p>Hi {escape(username)},</p>"
        f'<p>Please confirm your email address: <a href="{escape(link)}">verify my email</a>.</p>'
        f"<p>This link expires in {hours} hours. If you didn't create an account, ignore this email.</p>"
    )
    return f"Confirm your email for {config.PROJECT_NAME}", html


def password_reset_email(username: str, token: str) -> tuple[str, str]:
    link = _link("/reset-password", token)
    minutes = config.PASSWORD_RESET_EXPIRE_MINUTES
    html = (
        f"<p>Hi {escape(username)},</p>"
        f'<p>Someone asked to reset your password. <a href="{escape(link)}">Choose a new password</a>.</p>'
        f"<p>This link expires in {minutes} minutes and can be used once. "
        "If you didn't ask for this, you can ignore this email; your password stays unchanged.</p>"
    )
    return f"Reset your {config.PROJECT_NAME} password", html


def password_changed_email(username: str) -> tuple[str, str]:
    html = (
        f"<p>Hi {escape(username)},</p>"
        "<p>Your password was just changed and all other sessions were signed out. "
        "If this wasn't you, reset your password immediately and contact support.</p>"
    )
    return f"Your {config.PROJECT_NAME} password was changed", html
