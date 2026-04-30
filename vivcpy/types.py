from enum import Enum
from typing import TypeAlias, TypeVar

E = TypeVar("E", bound=Enum)
T = TypeVar("T")
OneOrMany: TypeAlias = T | list[T]
