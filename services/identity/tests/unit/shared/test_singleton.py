from app.shared.utils.singleton import singleton


def test_singleton_decorator() -> None:
    """Test that a class decorated with @singleton only instantiates a single shared instance."""

    @singleton
    class DatabaseConnection:
        def __init__(self, connection_string: str) -> None:
            self.connection_string = connection_string

    conn1 = DatabaseConnection("db://host1")
    conn2 = DatabaseConnection("db://host2")
    assert conn1 is conn2
    assert conn1.connection_string == "db://host1"
    assert conn2.connection_string == "db://host1"
