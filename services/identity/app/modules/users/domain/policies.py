"""
Policies: business decisions that need facts the entity does not hold (configuration, the clock).

Counting failed sign-ins and locking the account happen in one atomic database UPDATE
(`UserRepository.register_failed_login`), so concurrent wrong passwords cannot slip past the limit.
The policy decides *how long* the lock lasts; the repository applies it atomically.
"""

from datetime import datetime, timedelta


def lockout_expiry(*, now: datetime, lockout_minutes: int) -> datetime:
    """When an account locked at `now` may try to sign in again."""
    if now.tzinfo is None:
        raise ValueError("Lockout times require a timezone-aware datetime")
    return now + timedelta(minutes=lockout_minutes)
