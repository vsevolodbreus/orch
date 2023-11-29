import datetime as dt
import uuid
from importlib.metadata import distribution
from typing import Any, Dict, List, Optional

import fastapi as fa
import fastapi_utils.tasks as fastapi_tasks
from fastapi import Depends
from fastapi import status as http_status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

import orch.config as conf
import orch.schemas as schemas
from orch.database import async_session, get_session
from orch.logger import logger
from orch.models.flow import Flow
from orch.models.status import Status
from orch.webhook import report_on_flow

app = fa.FastAPI(
    title="orch",
    version=distribution("orch").version,
    openapi_url=None,
    docs_url=None,
    redoc_url=None,
)


@app.get("/", status_code=http_status.HTTP_200_OK)
async def index():
    return {
        "service": "orch",
        "version": distribution("orch").version,
    }


@app.get("/check", status_code=http_status.HTTP_200_OK)
async def healthcheck(session: AsyncSession = Depends(get_session)):
    """Returns 200 if all seems ok"""
    async with session:
        await session.execute(select(Flow).limit(1))
    return {"healthy": "yes"}


@app.get(
    "/flows/{flow_id}",
    status_code=http_status.HTTP_200_OK,
    response_model=schemas.ResponseFlow,
)
async def get_flow_by_id(
    flow_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
):
    """Get a flow by its unique id."""
    async with session:
        flow = await Flow.get_by_id(session, flow_id)
        if flow is None:
            raise fa.HTTPException(status_code=404, detail="no such flow")

        return schemas.ResponseFlow.from_model(flow)


@app.post(
    "/flows",
    status_code=http_status.HTTP_201_CREATED,
    response_model=schemas.ResponseFlow,
    response_model_exclude_unset=True,
)
async def run_flow(
    req: schemas.RequestNewFlow,
    session: AsyncSession = Depends(get_session),
):
    """Run a flow by its unique name and any provided arguments."""
    flow = Flow.from_req(req.name, req.args, req.webhook_url, req.priority)

    async with session:
        session.add(flow)
        await session.commit()
        logger.bind(flow_name=flow.name).bind(args=str(req.args)).bind(
            flow_id=str(flow.id)
        ).info("flow received")

        return schemas.ResponseFlow.from_model(flow)


@app.post("/hooks/flow/{flow_id}", status_code=http_status.HTTP_200_OK)
async def unblock_flow_by_id(
    flow_id: uuid.UUID,
    req: Dict[str, Any],
    session: AsyncSession = Depends(get_session),
):
    """Handles a generic flow webhook call.

    The provided data is supplied to the flow's first blocked task.
    """
    logger.bind(flow_id=str(flow_id)).bind(args=str(req)).info("flow webhook received")

    async with session:
        flow = await Flow.get_by_id(session, flow_id)
        if flow is None:
            raise fa.HTTPException(status_code=404, detail="no such flow")

        task = flow.get_next_blocked_task()
        if not task:
            raise fa.HTTPException(status_code=400, detail="flow already unblocked")

        task.args = {"webhook_request_body": req}
        task.status = Status.PENDING
        session.add(task)
        await session.commit()

        return schemas.ResponseFlow.from_model(flow)


@app.get(
    "/flows",
    status_code=http_status.HTTP_200_OK,
    response_model=schemas.ResponseExecutedFlows,
)
async def get_executed_flows(
    session: AsyncSession = Depends(get_session),
    name: Optional[str] = None,
    ids: Optional[List[uuid.UUID]] = None,
    created_from: Optional[dt.datetime] = None,
    created_to: Optional[dt.datetime] = None,
    priority: Optional[int] = None,
):
    """Return a list of executed flows matching given criteria."""

    query = select(Flow).order_by(Flow.created_at.desc())

    if name:
        query = query.filter(Flow.name == name)

    if ids:
        query = query.filter(Flow.id.in_(ids))

    if created_from:
        query = query.filter(Flow.created_at >= created_from)

    if created_to:
        query = query.filter(Flow.created_at <= created_to)

    if priority is not None:
        query = query.filter(Flow.priority == priority)

    async with session:
        items = (await session.execute(query)).fetchall()
        return schemas.ResponseExecutedFlows(
            count=len(items),
            flows=[
                schemas.ResponseFlow.from_model(flow._mapping[schemas.Flow])
                for flow in items
            ],
        )


@app.on_event("startup")
@fastapi_tasks.repeat_every(seconds=conf.tick_period / 1000, raise_exceptions=True)
async def run_tasks_periodically():
    """Find eligible tasks one by one and run them."""
    async with async_session() as session:
        while True:
            try:
                flow = await Flow.get_next_eligible(session)
                if flow is None:
                    return

                status = await flow.run_next_task()
                logger.bind(flow_name=flow.name).bind(flow_id=str(flow.id)).info(
                    f"task status after running: {status}"
                )
                await session.commit()

                if (
                    all(task.status == Status.SUCCESS for task in flow.tasks)
                    and flow.webhook_url
                ):
                    await report_on_flow(flow)

                logger.bind(flow_name=flow.name).bind(flow_id=str(flow.id)).bind(
                    flow_duration=flow.duration()
                ).bind(flow_duration_tasks=flow.duration(only_tasks=True)).info(
                    f"flow status: {flow.status()}"
                )

            except Exception as err:
                logger.opt(exception=err).error("task runner error")
                return


@app.post(
    "/retry/{flow_id}",
    status_code=http_status.HTTP_200_OK,
)
async def retry_failed_tasks(
    flow_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
):
    logger.bind(flow_id=str(flow_id)).info("retry failed tasks received")
    async with session:
        flow = await Flow.get_by_id(session, flow_id)
        if flow is None:
            raise fa.HTTPException(status_code=404, detail="no such flow")

        if any(task.status == Status.FAILURE for task in flow.tasks):
            for task in flow.tasks:
                if task.status == Status.FAILURE:
                    task.status = Status.PENDING
                    task.output = {}
                    task.updated_at = dt.datetime.utcnow()
                    task.started_at = None
                    task.finished_at = None
                    session.add(task)

            await session.commit()
            return schemas.ResponseFlow.from_model(flow)
        else:
            raise fa.HTTPException(
                status_code=400,
                detail="there is no failed tasks failed for this flow",
            )
