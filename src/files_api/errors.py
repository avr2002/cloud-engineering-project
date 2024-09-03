"""Custom error handlers for the Fast API application."""

import pydantic
from aws_embedded_metrics.logger.metrics_logger import MetricsLogger
from fastapi import (
    Request,
    status,
)
from fastapi.responses import JSONResponse
from loguru import logger

from files_api.metrics import metrics_ctx


# Fast API Docs on Middleware: https://fastapi.tiangolo.com/tutorial/middleware/
async def handle_broad_exceptions__middleware(request: Request, call_next):
    """Handle any exception that goes unhandled by a more specific exception handler."""
    try:
        return await call_next(request)
    except Exception as exc:  # pylint: disable=broad-except
        logger.exception("Unhandled Exception: {}", exc)

        metrics: MetricsLogger = metrics_ctx.get()
        if metrics:
            metrics.put_metric(key="UnhandledExceptions", value=1, unit="Count")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "message": "An unexpected error occurred.",
                "detail": "Internal Server Error",
            },
        )


# Fast API Docs on Error Handlers:
# https://fastapi.tiangolo.com/tutorial/handling-errors/?h=error#install-custom-exception-handlers
async def handle_pydantic_validation_error(request: Request, exc: pydantic.ValidationError) -> JSONResponse:
    """Handle Pydantic validation errors."""
    errors = exc.errors()
    logger.exception("Validation Error: {}", exc)
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "detail": [
                {
                    "msg": error["msg"],
                    "input": error["input"],
                }
                for error in errors
            ]
        },
    )
