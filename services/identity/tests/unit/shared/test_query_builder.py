from app.modules.users.infrastructure.persistence.models import Users
from app.shared.utils.query_builder import sqlalchemy_query_builder


def test_sqlalchemy_query_builder_basic() -> None:
    """Test that sqlalchemy_query_builder builds correct filters for basic types (string, boolean)."""
    expr_str = sqlalchemy_query_builder(Users, {"email": "ada"})
    sql_str = str(expr_str)
    assert "email" in sql_str
    assert "like" in sql_str.lower()
    expr_bool = sqlalchemy_query_builder(Users, {"is_active": True})
    sql_bool = str(expr_bool)
    assert "is_active" in sql_bool
    assert "true" in sql_bool.lower()


def test_sqlalchemy_query_builder_commands() -> None:
    """Test that sqlalchemy_query_builder parses and translates double-underscore commands (in, contains, isnull, comparisons)."""
    expr_in = sqlalchemy_query_builder(Users, {"email__in": "a@b.io,c@d.io"})
    assert "email" in str(expr_in)
    expr_contains = sqlalchemy_query_builder(Users, {"username__contains": "ada"})
    assert "username" in str(expr_contains)
    expr_isnull = sqlalchemy_query_builder(Users, {"locked_until__isnull": True})
    assert "locked_until" in str(expr_isnull)
    expr_isnotnull = sqlalchemy_query_builder(Users, {"locked_until__isnull": False})
    assert "locked_until" in str(expr_isnotnull)
    expr_comp = sqlalchemy_query_builder(Users, {"created_at__gte": "2026-01-01"})
    assert "created_at" in str(expr_comp)


def test_sqlalchemy_query_builder_edge_cases() -> None:
    """Test that sqlalchemy_query_builder handles OR logical joining, invalid attributes, and numeric values."""
    expr_num = sqlalchemy_query_builder(Users, {"failed_login_attempts": 3})
    assert "failed_login_attempts" in str(expr_num)

    expr_or = sqlalchemy_query_builder(Users, {"email": "ada", "is_active": True}, is_or=True)
    sql_or = str(expr_or)
    assert "or" in sql_or.lower()

    expr_invalid_attr = sqlalchemy_query_builder(Users, {"nonexistent_column": "value"})
    assert "nonexistent_column" not in str(expr_invalid_attr)

    expr_invalid_custom = sqlalchemy_query_builder(Users, {"invalid_field__eq": "value"})
    assert "invalid_field" not in str(expr_invalid_custom)
