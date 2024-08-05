"""
AWS Lambda handler using Mangum as an ASGI adapter for the FastAPI application.

Repository: https://github.com/jordaneremieff/mangum
"""

from mangum import Mangum

from files_api.main import create_app
from files_api.utils import (
    logger,
    metrics,
)

APP = create_app()

handler = Mangum(APP)

# Inject Lambda context for logging
handler = logger.inject_lambda_context(handler, clear_state=True)
handler = metrics.log_metrics(handler)
