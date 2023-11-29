"""Re-exports all tasks"""

import re
from importlib import import_module
from pathlib import Path

from orch.logger import logger
from orch.tasks.template import TaskTemplate

tasks = {}

for path in Path(__file__).parent.glob("*.py"):
    # ignore tasks
    if path.name.startswith("__") or path.name == "template.py":
        continue

    name = path.stem
    assert re.match(r"^[a-z0-9_]+$", name), f"bad task name {name}"
    task = import_module(f"orch.tasks.{name}")
    assert issubclass(task.Task, TaskTemplate), f"bad task class {name}"
    tasks[name] = task
    logger.bind(task_name=path.stem).debug("task template loaded")
