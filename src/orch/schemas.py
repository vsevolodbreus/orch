import datetime
import uuid
from typing import Any, Dict, List, Optional

import pydantic as pyd
from typing_extensions import Literal

from orch.flows import flows
from orch.models.flow import Flow
from orch.models.status import Status
from orch.models.task import Task
from orch.tasks import tasks


class Base(pyd.BaseModel):
    class Config:
        extra = "forbid"


class RequestNewFlow(Base):
    name: pyd.constr(strict=True, min_length=1)
    args: Dict[pyd.constr(strict=True, min_length=1), Any]
    webhook_url: Optional[pyd.AnyHttpUrl] = None
    priority: Optional[int] = 0

    @pyd.validator("name")
    def name_must_match_existing_flow(cls, v):
        assert v in flows, f"no such flow: {v}"
        return v

    @pyd.root_validator
    def args_must_match_flow_schema(cls, vals):
        assert "name" in vals, "no valid flow name provided"
        assert vals["name"] in flows, f"no such flow: {vals}"
        vals["args"] = vals.get("args") or {}
        flows[vals["name"]](**vals["args"])  # Ensure arguments schema.
        return vals


class ResponseTask(Base):
    id: uuid.UUID
    name: pyd.constr(strict=True, min_length=1)
    ordering: pyd.conint(strict=True, ge=0)
    status: Literal[tuple(status.value for status in Status)]
    output: Dict[str, Any]
    args: Dict[str, Any]
    updated_at: datetime.datetime
    finished_at: Optional[datetime.datetime] = None

    @staticmethod
    def from_model(task: Task) -> "ResponseTask":
        return ResponseTask(
            id=task.id,
            args=task.args,
            name=task.name,
            ordering=task.ordering,
            status=task.status.value,
            output=task.output,
            updated_at=task.updated_at,
            finished_at=task.finished_at,
        )


class ResponseFlow(RequestNewFlow):
    id: uuid.UUID
    created_at: datetime.datetime
    status: Literal[tuple(status.value for status in Status)]
    tasks: Optional[List[ResponseTask]]
    output: Optional[Dict[str, Any]]
    is_valid: Optional[bool]

    @staticmethod
    def from_model(flow: Flow) -> "ResponseFlow":
        return ResponseFlow(
            id=flow.id,
            name=flow.name,
            args=flow.args,
            created_at=flow.created_at,
            webhook_url=flow.webhook_url,
            status=flow.status().value,
            tasks=[ResponseTask.from_model(task) for task in flow.tasks],
            output=flow.final_output(),
        )


class ResponseTaskTemplate(Base):
    name: Literal[tuple(tasks.keys())]
    output: Dict[pyd.constr(strict=True, min_length=1), Any]


class ResponseFlowTemplate(Base):
    name: Literal[tuple(flows.keys())]
    args: Dict[pyd.constr(strict=True, min_length=1), Any]
    tasks: List[ResponseTaskTemplate]


class ResponseExecutedFlows(Base):
    count: pyd.conint(ge=0)
    flows: List[ResponseFlow]


class ResponseError(Base):
    status_code: pyd.conint(strict=True, ge=100, le=999)
    message: pyd.constr(strict=True, min_length=1)
