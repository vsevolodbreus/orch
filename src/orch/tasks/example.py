"""An example task that does nothing but wait"""

import asyncio
from datetime import datetime as dt

from orch.tasks.template import TaskTemplate


class Task(TaskTemplate):
    wait_time: int
    unique_id: int = 0

    class Output(TaskTemplate.Output):
        dummy_id: int
        dummy_slept: float

    async def __call__(self) -> Output:
        """Sleeps for a given amount of milliseconds."""
        started_at = dt.utcnow()
        await asyncio.sleep(self.wait_time / 1000.0)
        slept_for = (dt.utcnow() - started_at).total_seconds() * 1000
        return Task.Output(dummy_id=self.unique_id, dummy_slept=slept_for)
