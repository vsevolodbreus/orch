"""Provides environment variable configuration helpers."""

import dataclasses
import os
import re
from typing import Any, Callable

from dotenv import load_dotenv

# Contains the full set of accessible configuration values.
_confs = []


@dataclasses.dataclass
class Conf:
    """A configuration value accessible via an environment variable."""

    name: str
    into: Callable[[str], Any] = str
    default: Any = None
    required: bool = False

    def _check_def(self) -> None:
        """Throw an assertion error in case of bad config definition."""
        assert isinstance(self.name, str), f"conf {self.name} must be str"
        assert self.name, f"conf {self.name} must be non-empty"
        assert re.match(r"^[0-9a-z_]+$", self.name), f"conf {self.name} misnamed"
        assert callable(self.into), f"conf {self.name} `into` is not callable"
        if self.required:
            assert self.default is None, f"conf {self.name} has bad default"

    def _reify(self) -> Any:
        """Return a value the conf is referencing."""
        var = self.name.upper()
        val = os.getenv(var)

        if val is not None:
            val = val.strip("'\"")
            return self.into(val)

        if self.required:
            raise ValueError(f"mandatory env var {var} missing")

        return self.default


def need(conf: Conf) -> None:
    """Declare a strong yet gentle need that a config value be exposed.

    Raises AssertionError if called after a call to `expose`.
    """
    global _confs
    assert isinstance(_confs, list), "must not call `need` after `expose`"
    assert isinstance(conf, Conf), f"conf must be of type Conf, not {conf}"
    conf._check_def()
    _confs.append(conf)


def expose() -> None:
    """Exposes needed config values.

    Raises AssertionError if called more than once.
    """
    global _confs
    assert isinstance(_confs, list), "must not call `expose` twice"

    # Expose config values globally.
    for conf in _confs:
        globals()[conf.name] = conf._reify()

    # Get rid of the evidence.
    _confs = None


# Expose the configuration values.
need(Conf("environment", required=True))
need(Conf("application", default="orch"))
need(Conf("log_level", default="INFO"))
need(Conf("async_database_url", required=True))
need(Conf("database_url", required=True))
need(Conf("tick_period", into=int, default=1000))
need(Conf("webhook_num_of_retries", into=int, default=3))
need(Conf("webhook_timeout", into=int, default=5000))
need(Conf("webhook_pause_between_retries", into=int, default=100))
need(Conf("orch_url", required=True))

load_dotenv()
expose()
