import asyncio
import json
from datetime import datetime as dt

import httpx

import orch.config as conf
from orch import schemas
from orch.logger import logger
from orch.models.flow import Flow
from orch.models.status import Status


async def _call(url: str, data: str) -> None:
    """Actually calls the webhook with the provided payload."""
    async with httpx.AsyncClient(timeout=conf.webhook_num_of_retries / 1000) as client:
        resp = await client.post(
            url, headers={"content-type": "application/json"}, json=json.loads(data)
        )
        resp.raise_for_status()


async def report_on_flow(flow: Flow) -> None:
    """Calls the webhook URL with the given Flow's data."""
    assert flow.webhook_url, "flow lacks webhook_url"

    call_from = dt.utcnow()
    status = Status.PENDING

    with logger.contextualize(webhook_url=flow.webhook_url, flow_id=str(flow.id)):
        logger.info("Sending flow webhook")

        flow_data = schemas.ResponseFlow.from_model(flow).json()

        # Try calling the webhook until a 2XX response is received.
        for i in range(conf.webhook_num_of_retries):
            try:
                await _call(flow.webhook_url, flow_data)
                status = Status.SUCCESS
                break

            except TimeoutError as err:
                logger.opt(exception=err).warning("webhook timed out")
                if i != conf.webhook_num_of_retries - 1:
                    # pause between retries
                    await asyncio.sleep(conf.webhook_pause_between_retries / 1000)

            except Exception as err:
                logger.bind(flow_id=str(flow.id)).opt(exception=err).warning(
                    "webhook error"
                )
                break

        # Log status and duration.
        with logger.contextualize(
            webhook_duration=(dt.utcnow() - call_from).total_seconds(),
            webhook_status=status.value,
        ):
            if status == Status.PENDING:
                logger.warning("webhook")
            else:
                logger.info("webhook")
