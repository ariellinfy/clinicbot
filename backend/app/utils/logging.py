# backend/app/utils/logging.py
import os
import logging
from logging.config import dictConfig

# Idempotent setup: safe to call multiple times
def setup_logging() -> None:
    level = os.getenv("LOG_LEVEL", "INFO").upper()
    access_level = os.getenv("UVICORN_ACCESS_LOG_LEVEL", "INFO").upper()
    sql_level = os.getenv("SQL_LOG_LEVEL", "WARNING").upper()

    dictConfig({
        "version": 1,
        "disable_existing_loggers": False,  # keep uvicorn/fastapi loggers
        "formatters": {
            "default": {
                "format": "[%(levelname)s] %(asctime)s %(name)s: %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S",
            },
            # Optional JSON formatter (uncomment if you prefer JSON logs)
            # "json": {
            #     "()": "pythonjsonlogger.jsonlogger.JsonFormatter",
            #     "fmt": "%(levelname)s %(asctime)s %(name)s %(message)s",
            # }
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "default",  # or "json"
                "stream": "ext://sys.stdout",
            },
        },
        "root": {  # root logger for your app
            "level": level,
            "handlers": ["console"],
        },
        "loggers": {
            # Tame noisy libraries as needed
            "uvicorn.error":   {"level": level, "handlers": ["console"], "propagate": False},
            "uvicorn.access":  {"level": access_level, "handlers": ["console"], "propagate": False},
            "sqlalchemy.engine": {"level": sql_level, "handlers": ["console"], "propagate": False},
            "httpx": {"level": "WARNING"},
        },
    })

def get_logger(name: str | None = None) -> logging.Logger:
    return logging.getLogger(name if name else __name__)
