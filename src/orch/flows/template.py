"""Provides a Flow template that other Flows inherit."""

from typing import Any, Dict, List, Optional

import pydantic as pyd

from orch.tasks.template import TaskTemplate


class FlowTemplate(pyd.BaseModel):
    """A Base Flow template"""

    extra: Optional[Dict[str, Any]] = None

    class Config:
        extra = "forbid"

    def tasks(self) -> List[TaskTemplate]:
        """Returns the flow's tasks, instantiated."""
        raise NotImplementedError("`tasks` not implemented")
