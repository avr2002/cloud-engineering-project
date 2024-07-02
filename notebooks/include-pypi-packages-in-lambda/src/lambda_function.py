import json
import os
import numpy as np

BUCKET_NAME = "lambda-demo-bucket-amit"


def lambda_handler(event: dict, context):
    res = np.array([1, 2, 3, 4, 5]) + np.array([5, 4, 3, 2, 1])
    print(f"Result: {res}")
    return event
