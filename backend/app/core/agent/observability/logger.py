"""Agent-Logger: 结构化日志封装"""

import logging
import json
from datetime import datetime

def get_logger(name: str) -> logging.Logger:
    """返回带结构化格式的 Logger"""
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter(
            "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
        ))
        logger.addHandler(handler)
        logger.setLevel(logging.DEBUG)
    return logger

def log_json(logger: logging.Logger, event: str, **kwargs):
    """输出结构化 JSON 日志"""
    payload = {"event": event, "ts": datetime.utcnow().isoformat(), **kwargs}
    logger.info(json.dumps(payload, ensure_ascii=False))