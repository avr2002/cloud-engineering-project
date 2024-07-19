"""
AWS Lambda handler using Mangum as an ASGI adapter for the FastAPI application.
Repository: https://github.com/jordaneremieff/mangum
"""

from mangum import Mangum

from files_api.main import create_app

APP = create_app()

handler = Mangum(APP)
