from typing import Callable

from aws_embedded_metrics.logger.metrics_logger import MetricsLogger
from fastapi import (
    Request,
    Response,
)
from fastapi.routing import APIRoute
from loguru import logger

from files_api.monitoring.logger import (
    log_request_info,
    log_response_info,
)
from files_api.monitoring.metrics import metrics_ctx

# Global variable to track cold starts
cold_start = True


def log_lambda_cold_start():
    """Log the cold start of the Lambda function."""
    global cold_start
    logger.info(f"Cold Start: {cold_start}", **{"cold_start": cold_start})
    cold_start = False


class RouteHandler(APIRoute):
    """Custom router to add FastAPI context to logs."""

    def get_route_handler(self) -> Callable:
        original_route_handler = super().get_route_handler()

        async def route_handler(request: Request) -> Response:
            # Add request context to all logs
            request_context = {
                "path": request.url.path,
                "route": self.path,
                "method": request.method,
            }
            logger.configure(extra={"http": request_context})

            # Add metrics context to logs
            metrics: MetricsLogger = metrics_ctx.get()

            # @TODO: Trying to see difference b/w adding dimensions and properties; Remove any one of them later
            # READ MORE about dimensions and properties in AWS Embedded Metrics: https://github.com/awslabs/aws-embedded-metrics-python
            metrics.put_dimensions(request_context)
            # metrics.set_property(key="fastapi", value=context)

            # with logger.contextualize(http=request_context):
            log_lambda_cold_start()
            log_request_info(request)
            response: Response = await original_route_handler(request)
            log_response_info(response)
            return response

        return route_handler
