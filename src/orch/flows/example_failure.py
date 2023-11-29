"""An example flow that fails immediately"""

from typing import List

import pydantic as pyd

import orch.tasks.example as example_task
import orch.tasks.example_failure as example_failure_task
from orch.flows.template import FlowTemplate
from orch.tasks.template import TaskTemplate


class Flow(FlowTemplate):
    wait_time: pyd.conint(strict=True, ge=0, le=60 * 60 * 1000)

    def tasks(self) -> List[TaskTemplate]:
        return [
            example_failure_task.Task(),
            example_task.Task(unique_id=1, wait_time=self.wait_time),
        ]
