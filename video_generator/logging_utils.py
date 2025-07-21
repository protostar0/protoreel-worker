"""
Logging utilities for ProtoVideo.
Centralizes logger setup for all modules.
"""
import logging
import sys
import json

class GCPJSONFormatter(logging.Formatter):
    def format(self, record):
        log_record = {
            "message": record.getMessage(),
            "level": record.levelname,
            "time": self.formatTime(record, self.datefmt),
        }
        if hasattr(record, "task_id"):
            log_record["task_id"] = record.task_id
        return json.dumps(log_record)

def get_logger():
    logger = logging.getLogger("protoreel_worker")
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(GCPJSONFormatter())
    logger.handlers = [handler]
    logger.setLevel(logging.INFO)
    logger.propagate = False
    return logger 