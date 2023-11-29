"""An example flow that blocks on its (only) task. It can be unblocked only
with an external calls via webhook.
"""

from typing import List

import orch.tasks.example_blocked as example_task
from orch.flows.template import FlowTemplate
from orch.tasks.template import TaskTemplate


class Flow(FlowTemplate):
    def tasks(self) -> List[TaskTemplate]:
        return [example_task.Task()]
