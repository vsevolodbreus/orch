from datetime import datetime as dt
from typing import Any, Dict, Optional

import sqlalchemy as sql
import sqlalchemy.dialects.postgresql as psql

from orch.database import Base
from orch.exceptions import OrchException
from orch.logger import logger
from orch.models.status import Status
from orch.tasks import tasks


class Task(Base):
    """A sub-element of a Flow that can be run"""

    __tablename__ = "tasks"

    # A unique id representing a run Task.
    id = sql.Column(psql.UUID(as_uuid=True), primary_key=True, nullable=False)

    # Name of the Task template this Task is based on.
    name = sql.Column(sql.String, nullable=False)

    # Each Task belongs to a Flow.
    flow_id = sql.Column(
        psql.UUID(as_uuid=True), sql.ForeignKey("flows.id"), nullable=False
    )

    # The Task's ordering within the Flow. Tasks are executed in order.
    ordering = sql.Column(sql.Integer, nullable=False, index=True)

    # The Task's status.
    status = sql.Column(
        sql.Enum(Status), default=Status.PENDING, nullable=False, index=True
    )

    # Input arguments provided to this Task as arbitrary JSON.
    args = sql.Column(psql.JSONB, nullable=False)

    # The Task's results as an arbitrary JSON.
    output = sql.Column(psql.JSONB, default={}, nullable=False)

    # When the Task was last updated.
    updated_at = sql.Column(sql.DateTime, default=dt.utcnow, nullable=False)

    # When the Task started to run.
    started_at = sql.Column(sql.DateTime, nullable=True)

    # When the Task finished, either with success or failure.
    finished_at = sql.Column(sql.DateTime, nullable=True)

    def is_done(self) -> bool:
        """Return whether the Task is in a non-pending, non-running state."""
        return self.status not in (Status.PENDING, Status.BLOCKED)

    def duration(self) -> Optional[float]:
        # how long was this task running in seconds
        if self.is_done():
            return (self.finished_at - self.started_at).total_seconds()

        return None

    async def run(self, outputs: Dict[str, Any]) -> None:
        """Run this Task."""
        now = dt.utcnow()
        self.updated_at = now
        self.started_at = now
        self.finished_at = None

        with logger.contextualize(task_id=str(self.id), task_name=self.name):
            logger.bind(task_status=self.status.value).info("running task")

            try:
                # Run task within context.
                task = tasks[self.name].Task(**self.args)
                default_args = {"flow_id": self.flow_id}
                task._context.update({**default_args, **outputs})
                output = await task()

                # Set its status and output depending on behaviour.
                if output is not None:
                    self.status = Status.SUCCESS
                    self.output = output.dict()
                else:
                    self.status = Status.BLOCKED
                    logger.bind(task_status=self.status.value).info("task blocked")

            except (OrchException, Exception) as err:
                logger.opt(exception=err).error("task error")
                self.output = {
                    "error": err.message
                    if isinstance(err, OrchException)
                    else "internal server error"
                }
                self.status = Status.FAILURE

            finally:
                now = dt.utcnow()
                self.updated_at = now
                # If done, we log the time diff.
                if self.is_done():
                    self.finished_at = now
                    logger.bind(task_status=self.status.value).bind(
                        task_duration=self.duration()
                    ).info("task finished")
