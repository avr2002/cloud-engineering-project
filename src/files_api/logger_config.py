from __future__ import annotations

import json
import os
import sys

import loguru
from loguru import logger


def sink_serializer(message: loguru.Message):
    record = message.record
    log_record = {
        "timestamp": record["time"].timestamp(),
        "level": record["level"].name,
        "location": f"{record['file'].name}:{record['line']}:{record['function']}",
        "message": record["message"],
    }
    
    extra = record["extra"]
    if extra:
        log_record.update(json.loads(extra))
    
    serialized_record = json.dumps(log_record, default=str)
    print(serialized_record)
    return serialized_record



def serialize_extra_keys(record: loguru.Record) -> loguru.Record:
    extra = record["extra"]
    if extra:
        record["extra"] = json.dumps(extra)
    return record


logging_config = {
    "handlers": [
        {
            "sink": sys.stdout,
            "format": "{time:YYYY-MM-DD HH:mm:ss,SSSZZ} | {level} | {file}:{line}:{function} | {message} | {extra}",
            "level": os.environ["LOG_LEVEL"],
            "filter": serialize_extra_keys,
            # "serialize": True,
        },
        # {
        #     "sink": sink_serializer,
        #     "level": os.environ["LOG_LEVEL"],
        # }
    ],
}


# Remove the default logger config and add custom configurations
logger.remove()
logger.configure(**logging_config)
