"""An example flow that simply waits for a given amount of time, but using a
variable number of tasks"""

from typing import List

import pydantic as pyd

import orch.tasks.example as example_task
from orch.flows.template import FlowTemplate
from orch.tasks.template import TaskTemplate


class Flow(FlowTemplate):
    # wait_time: how long the flow will wait
    wait_time: pyd.conint(strict=True, ge=0, le=60 * 60)
    # num_of_tasks: amount of example tasks this flow will contain
    num_of_tasks: pyd.conint(strict=True, ge=1, le=50)

    def tasks(self) -> List[TaskTemplate]:
        delay = self.wait_time / self.num_of_tasks
        return [
            example_task.Task(wait_time=delay, unique_id=i)
            for i in range(self.num_of_tasks)
        ]
