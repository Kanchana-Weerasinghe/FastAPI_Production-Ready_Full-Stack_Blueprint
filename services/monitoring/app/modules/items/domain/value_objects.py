"""
VALUE OBJECTS: small values that check and clean themselves when they are created.

If the input is wrong they raise, so an invalid name or code can never exist anywhere in the code and no
other layer has to check it again. They cannot be changed after creation (`frozen=True`).

    ItemName("  Blue   pen ").value  ->  "Blue pen"     (extra spaces removed)
    ItemName("ab")                    ->  raises InvalidItemName
    ItemCode(" itm-001 ").value       ->  "ITM-001"      (trimmed, upper case)
    ItemCode("ITM 001")               ->  raises InvalidItemCode (space not allowed)

`ItemStatus` lists the states a item can be in; the entity decides which changes are allowed.
"""

import re
from dataclasses import dataclass
from enum import StrEnum

from app.modules.items.domain.exceptions import InvalidItemCode, InvalidItemName

NAME_MIN_LENGTH = 3
NAME_MAX_LENGTH = 120
CODE_MAX_LENGTH = 20
CODE_PATTERN = re.compile(r"^[A-Z0-9][A-Z0-9-]{1,19}$")  # 2-20 chars: letters, digits, dashes


class ItemStatus(StrEnum):
    ACTIVE = "active"
    ARCHIVED = "archived"


@dataclass(frozen=True, slots=True)
class ItemName:
    value: str

    def __post_init__(self) -> None:
        cleaned = " ".join(self.value.split())  # 1. clean: trim and collapse spaces
        if not NAME_MIN_LENGTH <= len(cleaned) <= NAME_MAX_LENGTH:  # 2. check the rule
            raise InvalidItemName(f"Name must contain {NAME_MIN_LENGTH}-{NAME_MAX_LENGTH} characters")
        object.__setattr__(self, "value", cleaned)  # 3. keep the cleaned value


@dataclass(frozen=True, slots=True)
class ItemCode:
    value: str

    def __post_init__(self) -> None:
        cleaned = self.value.strip().upper()
        if not CODE_PATTERN.match(cleaned):
            raise InvalidItemCode("Code must be 2-20 letters, digits or dashes, e.g. ITM-001")
        object.__setattr__(self, "value", cleaned)
