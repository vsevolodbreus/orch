"""Provides a Task template that other Tasks inherit."""

import inspect
from typing import Any, Dict, List, Optional, Set, Type

import pydantic as pyd


class TaskTemplate(pyd.BaseModel):
    """Describes a Task's inputs and base functionality."""

    __slots__ = ("_context",)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        object.__setattr__(self, "_context", {})

    extra: Optional[Dict[str, Any]] = None

    class Config:
        extra = "forbid"

    class Output(pyd.BaseModel):
        """Describes a Tasks's outputs."""

        class Config:
            extra = "forbid"

    async def __call__(self) -> Optional[Output]:
        """Perform's a Task's function.

        Returns the new Task's status and its results."""
        raise NotImplementedError("task method `__call__` not implemented")

    @classmethod
    def get_name(cls):
        """Return the Task's name"""
        for _cls in [cls] + list(cls.__bases__):
            cls_name = inspect.getmodule(_cls).__name__
            if cls_name.startswith("orch.tasks."):
                return cls_name.split(".")[2]

        raise ValueError("could not determine task name")

    def assert_context(self, name: str) -> Optional[Any]:
        """Get a value from the task's context"""
        assert name in self._context, "missing context value: {name}"
        return self._context[name]

    def context(self, name: str) -> Optional[Any]:
        """Get a value from the task's context, or None if not present."""
        return self._context.get(name)

    def tasks(self) -> List["TaskTemplate"]:
        """Returns the task itself."""
        return [self]
