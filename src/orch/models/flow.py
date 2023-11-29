import uuid
from datetime import datetime as dt
from typing import Any, Dict, Optional

import sqlalchemy as sql
import sqlalchemy.dialects.postgresql as psql
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.ext.orderinglist import ordering_list
from sqlalchemy.future import select
from sqlalchemy.orm import aliased, relationship

from orch.database import Base
from orch.flows import flows
from orch.logger import logger
from orch.models.status import Status
from orch.models.task import Task


class Flow(Base):
    """Describes a Flow in the database, a series of Tasks."""

    __tablename__ = "flows"

    # A unique id of a running Flow
    id = sql.Column(psql.UUID(as_uuid=True), primary_key=True, nullable=False)

    # Name of a Flow template this Flow is based on
    name = sql.Column(sql.String, nullable=False)

    # Input arguments provided to this Flow as arbitrary JSON
    args = sql.Column(psql.JSONB, nullable=False)

    # A webhook URL to call upon this Flow's termination
    webhook_url = sql.Column(sql.String, nullable=True)

    # A list of tasks associated with this Flow
    tasks = relationship(
        "Task",
        order_by="Task.ordering",
        collection_class=ordering_list("ordering"),
        lazy="selectin",
    )

    # When the Flow was created.
    created_at = sql.Column(sql.DateTime, default=dt.utcnow, nullable=False)

    # What is the priority in the queue at execution, zero default.
    priority = sql.Column(sql.Integer, default=0, nullable=False)

    @staticmethod
    def from_req(
        name: str,
        args: Dict[str, Any],
        webhook_url: Optional[str] = None,
        priority: Optional[int] = 0,
    ) -> "Flow":
        """Create and return a Flow with its associated Tasks"""
        assert name in flows, f"cannot create undefined flow: {name}"
        args = flows[name](**args)  # Ensure arguments schema matches.

        flow = Flow(
            id=uuid.uuid4(),
            name=name,
            args=args.dict(),
            webhook_url=webhook_url,
            priority=priority,
        )

        for i, task in enumerate(flows[name].tasks(args)):
            flow.tasks.append(
                Task(
                    id=uuid.uuid4(),
                    ordering=i,
                    args=task.dict(),
                    name=task.__class__.get_name(),
                    flow_id=flow.id,
                )
            )

        return flow

    @staticmethod
    async def get_by_id(
        session: AsyncSession, flow_id: uuid.UUID, lock=False
    ) -> Optional["Flow"]:
        """Get a Flow by its unique id."""
        q = select(Flow).filter(Flow.id == flow_id).limit(1)
        if lock:
            q = q.with_for_update(skip_locked=False)

        r = (await session.execute(q)).first()
        return r._mapping[Flow] if r else None

    def status(self) -> Status:
        """Get the Flow's status, based on the statuses of its Tasks."""
        for task in self.tasks:
            for exp_status in (Status.FAILURE, Status.PENDING, Status.BLOCKED):
                if task.status == exp_status:
                    return exp_status

        return Status.SUCCESS

    def duration(self, only_tasks=False) -> Optional[float]:
        # calculates duration in seconds of a success flow
        if self.status() != Status.SUCCESS:
            return None

        if only_tasks:
            # used when we want to see how much have all tasks took to run
            # without possibly delays in between each task.
            return sum(task.duration() for task in self.tasks)

        return (
            max(task.finished_at for task in self.tasks) - self.created_at
        ).total_seconds()

    def outputs(self) -> Dict[str, Any]:
        """Return the Flow's collected Task outputs."""
        return {
            task.id: task.output
            for task in self.tasks
            if task.output is not None and task.status != Status.PENDING
        }

    def final_output(self) -> Dict[str, Any]:
        """Returns the final output of the flow"""
        return self.tasks[-1].output

    def set_pending_tasks_failed(self):
        """Sets all non-finished tasks to status FAILURE.

        After a single task fails, all future tasks are set to FAILED so they
        are no longer picked up as candidate tasks for the flow runner.
        """
        for task in self.tasks:
            if task.status == Status.PENDING:
                task.status = Status.FAILURE

    def get_next_blocked_task(self) -> Optional[Task]:
        """Get the first flow task that is of status BLOCKED, if any."""
        for task in self.tasks:
            if task.status == Status.BLOCKED:
                return task

        return None

    def get_blocked_task_by_name(self, task_name) -> Optional[Task]:
        """Get a named flow task that is of status BLOCKED, if any."""
        for task in self.tasks:
            if task.status == Status.BLOCKED and task.name == task_name:
                return task
        return None

    @staticmethod
    async def get_blocked_task_by_name_and_block_db(
        session: AsyncSession, flow_id, task_name
    ) -> Optional[Task]:
        """Get a task that is of status BLOCKED, if any."""
        q = (
            select(Task)
            .join(Flow)
            .filter(Flow.id == flow_id)
            .filter(Task.name == task_name)
            .filter(Task.status == Status.BLOCKED)
            .with_for_update(of=Task, skip_locked=True)
            .execution_options(populate_existing=True)
            .limit(1)
        )

        r = (await session.execute(q)).first()
        found_task = r._mapping[Task] if r else None

        return found_task

    @staticmethod
    async def get_next_eligible(session: AsyncSession) -> Optional["Flow"]:
        """Get the next Flow that is eligible to be run.

        This is done by finding pending tasks within flows that contain no
        running or failed tasks, as these signify flows that are being run by
        another instance or flows that have failed altogether.
        """
        flow_blocked = aliased(Flow)

        q_blocked = (
            select(flow_blocked.id)
            .join(Task)
            .filter(Task.status == Status.BLOCKED)
            .filter(flow_blocked.id == Flow.id)
            .exists()
        )

        q = (
            select(Flow)
            .join(Task)
            .filter(Task.status == Status.PENDING)
            .filter(~q_blocked)
            .with_for_update(skip_locked=True)
            .order_by(sql.text("priority desc"))
            .limit(1)
        )

        r = (await session.execute(q)).first()
        found_flow = r._mapping[Flow] if r else None

        return found_flow

    async def run(self) -> None:
        """Run all pending Tasks until Flow finishes."""
        while True:
            try:
                status = await self.run_next_task()
                if status is None or status == Status.FAILURE:
                    return
            except Exception as err:
                logger.opt(exception=err).error("error in running task")
                return

    async def run_next_task(self) -> Optional[Status]:
        """Run this Flow's next eligible Task, returning its new Status."""
        with logger.contextualize(
            flow_name=self.name,
            flow_id=str(self.id),
        ):
            for task in self.tasks:
                if task.status == Status.SUCCESS:
                    continue  # Skip already successful tasks.

                # if a task is blocked, skip this flow until unblocked.
                if task.status == Status.BLOCKED:
                    break

                if task.status == Status.FAILURE:
                    logger.warning("will not rerun failed task")
                    break

                # Collect all the Task outputs of the Flow.
                outputs = self.outputs()
                outputs = {
                    key: val for outs in outputs.values() for key, val in outs.items()
                }

                try:
                    outputs["flow"] = self
                    await task.run(outputs)
                    if task.status == Status.FAILURE:
                        self.set_pending_tasks_failed()

                except Exception as err:
                    logger.opt(exception=err).error("task error")
                    self.set_pending_tasks_failed()

                # Only run a single Task and no more.
                return task.status

            return None
