"""Provides an example task that fails"""

from typing import Optional

from orch.exceptions import OrchException
from orch.tasks.template import TaskTemplate


class Task(TaskTemplate):
    """Fails with status FAILURE."""

    async def __call__(self) -> Optional[TaskTemplate.Output]:
        raise OrchException("failed on purpose")
