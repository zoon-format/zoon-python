from typing import Any, TypeAlias

ZoonValue: TypeAlias = str | int | float | bool | None | list | dict
ZoonData: TypeAlias = list[dict[str, ZoonValue]] | dict[str, ZoonValue]

TYPE_STRING = "s"
TYPE_INTEGER = "i"
TYPE_NUMBER = "n"
TYPE_BOOLEAN = "b"
TYPE_AUTO_INCREMENT = "i+"

MARKER_NULL = "~"

BOOL_TRUE = "1"
BOOL_FALSE = "0"
INLINE_BOOL_TRUE = "y"
INLINE_BOOL_FALSE = "n"
