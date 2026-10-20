"""
platform-kit: technical building blocks shared by every domain service.

Nothing in this package knows about a business domain. Services import it for cross-cutting
concerns (settings, logging, unit of work, errors, middleware, health, auth, HTTP clients) and keep
their business rules in their own `domain/` and `application/` layers.
"""

__version__ = "0.1.0"
