from typing import Any

from sqlalchemy.sql.expression import and_, or_

SQLALCHEMY_QUERY_MAPPER = {
    "eq": "__eq__",
    "ne": "__ne__",
    "lt": "__lt__",
    "lte": "__le__",
    "gt": "__gt__",
    "gte": "__ge__",
    "contains": "contains",
}


def sqlalchemy_query_builder(model_class: Any, search_option_dict: dict[str, Any], is_or: bool = False) -> Any:
    """
    Dynamically builds SQLAlchemy filter expressions from a dictionary of options.

    Supports basic field matching and advanced 'Django-style' double-underscore filters.

    Args:
        model_class: The SQLAlchemy model class to build filters for.
        search_option_dict: A dictionary where keys are field names or field__command.
        is_or: If True, filters are joined with OR instead of AND.

    Supported Commands (__command):
        eq: Equals
        ne: Not Equals
        lt/lte: Less Than / Less Than or Equal
        gt/gte: Greater Than / Greater Than or Equal
        contains: Case-insensitive partial string match
        in: Matches any value in a comma-separated string
        isnull: Checks if a column is NULL (expects boolean)

    Examples:
        - Basic: {"title": "Task"} -> title ILIKE '%Task%'
        - Advanced: {"status__eq": "active"} -> status == 'active'
        - Range: {"price__gte": 100} -> price >= 100
        - In: {"id__in": "id1,id2"} -> id.in_(['id1', 'id2'])
    """
    sql_alchemy_filter_options = []
    copied_dict = search_option_dict.copy()
    for key in search_option_dict:
        attr = getattr(model_class, key, None)
        if attr is None:
            continue
        option_from_dict = copied_dict.pop(key)
        if isinstance(option_from_dict, bool):
            sql_alchemy_filter_options.append(attr.is_(option_from_dict))
        elif isinstance(option_from_dict, (int, float)):
            sql_alchemy_filter_options.append(attr == option_from_dict)
        elif isinstance(option_from_dict, str):
            sql_alchemy_filter_options.append(attr.ilike("%" + option_from_dict + "%"))
    for custom_option in copied_dict:
        if "__" not in custom_option:
            continue
        key, command = custom_option.split("__")
        attr = getattr(model_class, key, None)
        if attr is None:
            continue
        option_from_dict = copied_dict[custom_option]
        if command == "in":
            sql_alchemy_filter_options.append(attr.in_([option.strip() for option in option_from_dict.split(",")]))
        elif command in SQLALCHEMY_QUERY_MAPPER.keys():
            mapper_command = SQLALCHEMY_QUERY_MAPPER[command]
            if mapper_command == "contains":
                sql_alchemy_filter_options.append(attr.ilike(f"%{option_from_dict}%"))
            else:
                sql_alchemy_filter_options.append(getattr(attr, mapper_command)(option_from_dict))
        elif command == "isnull":
            bool_command = "__eq__" if option_from_dict else "__ne__"
            sql_alchemy_filter_options.append(getattr(attr, bool_command)(None))

    if is_or:
        return or_(*sql_alchemy_filter_options)
    return and_(True, *sql_alchemy_filter_options)
