import fastapi
import fastapi.exceptions
import pydantic as pyd
import starlette.exceptions
from fastapi.encoders import jsonable_encoder

import orch.config as conf
import orch.routes
import orch.schemas as schemas
from orch.flows import flows

app = orch.routes.app


@app.exception_handler(starlette.exceptions.HTTPException)
async def handle_http_exceptions(_, exc):
    """Converts each HTTP exception to a nice JSON response."""
    return fastapi.responses.JSONResponse(
        jsonable_encoder(
            schemas.ResponseError(status_code=exc.status_code, message=str(exc.detail))
        ),
        status_code=exc.status_code,
    )


@app.exception_handler(500)
async def handle_internal_server_error(*_):
    """Converts each internal server error to a nice JSON response."""
    return fastapi.responses.JSONResponse(
        jsonable_encoder(
            schemas.ResponseError(status_code=500, message="internal server error")
        ),
        status_code=500,
    )


@app.exception_handler(pyd.error_wrappers.ValidationError)
@app.exception_handler(fastapi.exceptions.RequestValidationError)
async def handle_pydantic_error(_, exc):
    return fastapi.responses.JSONResponse(
        jsonable_encoder(
            schemas.ResponseError(
                status_code=400, message=str(exc) or "malformed request"
            )
        ),
        status_code=400,
    )


if __name__ == "__main__":
    from uvicorn import run as run_server

    run_server("orch:app", host="0.0.0.0", port=8000, log_level="debug")
