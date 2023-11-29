import re
from importlib import import_module
from pathlib import Path

from orch.flows.template import FlowTemplate
from orch.logger import logger

flows = {}

for path in Path(__file__).parent.glob("*.py"):
    # Ignore flows
    if path.name.startswith("__") or path.name == "template.py":
        continue

    name = path.stem
    assert re.match(r"^[a-z][a-z0-9_]+$", name), f"bad flow name {name}"
    flow = import_module(f"orch.flows.{name}")
    assert issubclass(flow.Flow, FlowTemplate), f"bad flow class {name}"
    flows[name] = flow.Flow
    logger.bind(flow_name=path.stem).debug("flow template loaded")
