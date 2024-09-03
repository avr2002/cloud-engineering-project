from typing import Callable

from aws_embedded_metrics.logger.metrics_logger import MetricsLogger
from fastapi import (
    Request,
    Response,
)
from fastapi.routing import APIRoute
from loguru import logger

from files_api.metrics import metrics_ctx

# Global variable to track cold starts
cold_start = True


def log_lambda_cold_start():
    """Log the cold start of the Lambda function."""
    global cold_start
    logger.info("Cold Start", **{"cold_start": cold_start})
    cold_start = False


class RouteHandler(APIRoute):
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
            
            # Add metrics context to logs
            metrics: MetricsLogger = metrics_ctx.get()
            metrics.set_property(key="fastapi", value=context)
            
            with logger.contextualize(fastapi=context):
                log_lambda_cold_start()
                return await original_route_handler(request)

        return route_handler
