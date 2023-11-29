"""An example flow that simply waits for a given amount of time"""

from typing import List

import pydantic as pyd

import orch.tasks.example as example_task
from orch.flows.template import FlowTemplate
from orch.tasks.template import TaskTemplate


class Flow(FlowTemplate):
    # wait_time: how long the flow will wait
    wait_time: pyd.conint(strict=True, ge=0, le=60 * 60 * 1000)

    def tasks(self) -> List[TaskTemplate]:
        return [
            example_task.Task(wait_time=self.wait_time / 3),
            example_task.Task(wait_time=self.wait_time / 3 * 2),
        ]
