from typing import Callable

from aws_lambda_powertools import (
    Logger,
    Metrics,
    Tracer,
)
from fastapi import (
    Request,
    Response,
)
from fastapi.routing import APIRoute

logger: Logger = Logger()
metrics: Metrics = Metrics()
tracer: Tracer = Tracer()


async def add_correlation_id(request: Request, call_next):
    """Middleware to add correlation ID to logs and response headers."""
    # Get the correlation ID from the incoming request headers
    correlation_id = request.headers.get("X-Correlation-ID", None)
    if not correlation_id:
        # If empty, use request ID from AWS Context
        # .get() method cannot be used with `request.scope`, thus using try-except to add a default value for local development
        try:
            correlation_id = request.scope["aws.context"].aws_request_id
        except KeyError:
            correlation_id = "local-development"

    # Add correlation ID to logs
    logger.set_correlation_id(correlation_id)

    response = await call_next(request)

    # Return correlation ID in response headers
    response.headers["X-Correlation-ID"] = correlation_id
    return response


class LoggerRouteHandler(APIRoute):
    """Custom router to add FastAPI context to logs."""

    def get_route_handler(self) -> Callable:
        original_route_handler = super().get_route_handler()

        async def route_handler(request: Request) -> Response:
            # Add fastapi context to logs
            context = {
                "path": request.url.path,
                "route": self.path,
                "method": request.method,
            }
            logger.append_keys(fastapi=context)
            logger.info("Request Received.")

            return await original_route_handler(request)

        return route_handler
