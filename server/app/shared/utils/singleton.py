from typing import Any, TypeVar, cast

T = TypeVar("T")


def singleton(class_: type[T]) -> type[T]:
    """A class decorator to implement the Singleton design pattern."""
    instances: dict[type[T], T] = {}

    def getinstance(*args: Any, **kwargs: Any) -> T:
        if class_ not in instances:
            instances[class_] = class_(*args, **kwargs)
        return instances[class_]

    return cast(type[T], getinstance)
