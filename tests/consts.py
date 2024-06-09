"""Constant values used for tests."""

from pathlib import Path
from uuid import uuid4

THIS_DIR = Path(__file__).parent
PROJECT_DIR = (THIS_DIR / "../").resolve()

TEST_BUCKET_NAME = f"test-bucket-cloud-course-{str(uuid4())[:4]}"
