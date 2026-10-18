from app.modules.todos.infrastructure.persistence.models import Todos
from app.shared.utils.query_builder import sqlalchemy_query_builder


def test_sqlalchemy_query_builder_basic() -> None:
    """Test that sqlalchemy_query_builder builds correct filters for basic types (string, boolean)."""
    expr_str = sqlalchemy_query_builder(Todos, {"title": "Laundry"})
    sql_str = str(expr_str)
    assert "title" in sql_str
    assert "like" in sql_str.lower()
    expr_bool = sqlalchemy_query_builder(Todos, {"is_completed": True})
    sql_bool = str(expr_bool)
    assert "is_completed" in sql_bool
    assert "true" in sql_bool.lower()


def test_sqlalchemy_query_builder_commands() -> None:
    """Test that sqlalchemy_query_builder parses and translates double-underscore commands (in, contains, isnull, comparisons)."""
    expr_in = sqlalchemy_query_builder(Todos, {"title__in": "task1,task2"})
    assert "title" in str(expr_in)
    expr_contains = sqlalchemy_query_builder(Todos, {"title__contains": "clean"})
    assert "title" in str(expr_contains)
    expr_isnull = sqlalchemy_query_builder(Todos, {"description__isnull": True})
    assert "description" in str(expr_isnull)
    expr_isnotnull = sqlalchemy_query_builder(Todos, {"description__isnull": False})
    assert "description" in str(expr_isnotnull)
    expr_comp = sqlalchemy_query_builder(Todos, {"created_at__gte": "2026-01-01"})
    assert "created_at" in str(expr_comp)


def test_sqlalchemy_query_builder_edge_cases() -> None:
    """Test that sqlalchemy_query_builder handles OR logical joining, invalid attributes, and numeric values."""
    expr_num = sqlalchemy_query_builder(Todos, {"user_id": 123})
    assert "user_id" in str(expr_num)

    expr_or = sqlalchemy_query_builder(Todos, {"title": "Laundry", "is_completed": True}, is_or=True)
    sql_or = str(expr_or)
    assert "or" in sql_or.lower()

    expr_invalid_attr = sqlalchemy_query_builder(Todos, {"nonexistent_column": "value"})
    assert "nonexistent_column" not in str(expr_invalid_attr)

    expr_invalid_custom = sqlalchemy_query_builder(Todos, {"invalid_field__eq": "value"})
    assert "invalid_field" not in str(expr_invalid_custom)
