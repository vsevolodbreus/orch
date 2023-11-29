"""Provides a global JSON logger to stderr."""

import json
import logging
import sys
import traceback

from loguru import logger

import orch.config as conf


def _stderr_json_sink(msg: dict) -> None:
    """Logs a message to stderr as json."""
    inp = msg.record
    out = {}

    if "level" in inp:
        out["level"] = inp["level"].name

    out["application"] = conf.application
    out["environment"] = conf.environment

    if "message" in inp:
        out["message"] = inp["message"].strip()

    if "time" in inp:
        out["timestamp"] = inp["time"].isoformat()

    for key, val in inp.get("extra", {}).items():
        if key not in out:
            out[key] = val

    if inp.get("exception") is not None:
        exc = inp["exception"]
        out["error"] = f"{type(exc).__name__}: {exc}"
        out["error_stacktrace"] = traceback.format_exc()

    sys.stderr.write(json.dumps(out, ensure_ascii=False, separators=(",", ":")))
    sys.stderr.write("\n")
    sys.stderr.flush()


class InterceptHandler(logging.Handler):
    """Used to route logging's log to the loguru sink."""

    def emit(self, record):
        try:
            # Get corresponding Loguru level if it exists.
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        # Find caller from where the logged message originated.
        frame, depth = logging.currentframe(), 2
        while frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(
            level, record.getMessage()
        )


# Remove charset normalizer in order to get rid of ascii probing
logging.getLogger("charset_normalizer").disabled = True

# Disable loguru's default logger.
logger.remove()

# Route all default logs to the loguru sink.
logging.basicConfig(handlers=[InterceptHandler()], level=0)
logging.root.handlers = [InterceptHandler()]

# Get rid of uvicorn loggers
for el in ["uvicorn.error", "uvicorn.access"]:
    bad_log = logging.getLogger(el)
    bad_log.handlers = [InterceptHandler()]
    bad_log.propagate = 0

# Force various dependencies to pipe down.
for el in ["httpx"]:
    logging.getLogger(el).setLevel(conf.log_level)

# Only use a single sink -- JSON messages to stderr.
logger.add(
    _stderr_json_sink,
    level=conf.log_level,
    colorize=False,
    diagnose=conf.environment != "production",
    enqueue=False,
)
