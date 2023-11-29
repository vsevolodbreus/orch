"""An example task which returns nothing for result which means it is blocked"""

from typing import Any, Dict, Optional

from orch.tasks.template import TaskTemplate


class Task(TaskTemplate):
    webhook_request_body: Optional[Dict[str, Any]] = None

    class Output(TaskTemplate.Output):
        unblocked_due_to: Dict[str, Any]

    async def __call__(self) -> Optional[Output]:
        if self.webhook_request_body is None:
            return None

        return Task.Output(unblocked_due_to=self.webhook_request_body)
