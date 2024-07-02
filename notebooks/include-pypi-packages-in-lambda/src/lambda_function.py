import json
import os
import requests


BUCKET_NAME = "lambda-demo-bucket-amit"

def lambda_handler(event: dict, context):
    return {
        "text": requests.get("https://www.wikipedia.org").text[:500]
    }