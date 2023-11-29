"""Provides a Task status."""

import enum


@enum.unique
class Status(enum.Enum):
    """Status of an instantiated Flow or Task"""

    def _generate_next_value_(name, *_):  # noqa: N805
        return name.lower()

    PENDING = enum.auto()
    SUCCESS = enum.auto()
    FAILURE = enum.auto()
    BLOCKED = enum.auto()  # Waiting for external action.
