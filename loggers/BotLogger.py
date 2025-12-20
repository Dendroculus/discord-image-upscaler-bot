import logging
import logging.config
import os
import sys
from typing import Union, Dict

DEFAULT_LOG_DIR = "logs"
DEFAULT_LOG_FILE = "app.log"

def ensure_log_dir(path: str) -> None:
    """
    Ensure the directory for log files exists.
    """
    os.makedirs(path, exist_ok=True)

def init_logging(
    log_dir: str = DEFAULT_LOG_DIR,
    log_file: str = DEFAULT_LOG_FILE,
    level: Union[str, int] = None,
    backup_count: int = 30,
    library_levels: Dict[str, Union[str, int]] = None
) -> None:
    """
    Initialize a robust logging configuration with console and file handlers.
    
    Args:
        log_dir (str): Directory to store log files. Defaults to "logs".
        log_file (str): Name of the log file. Defaults to "app.log".
        level (str | int): Root logging threshold. Defaults to env var or INFO.
        backup_count (int): Number of days to keep historical logs. Defaults to 30.
        library_levels (Dict[str, str|int]): Dictionary of library names and their 
                                             log levels to override/silence noise.
    """
    if level is None:
        level = os.getenv("LOG_LEVEL", "INFO")

    ensure_log_dir(log_dir)
    log_path = os.path.join(log_dir, log_file)

    file_fmt = "%(asctime)s %(levelname)-8s [%(name)s] %(message)s"
    datefmt = "%Y-%m-%d %H:%M:%S"

    logging_config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "file_format": {"format": file_fmt, "datefmt": datefmt},
        },
        "handlers": {
            "console": {
                "class": "rich.logging.RichHandler",
                "level": level,
                "rich_tracebacks": True,
                "markup": True,
                "show_time": True,
                "show_path": False,
            },
            "file": {
                "class": "logging.handlers.TimedRotatingFileHandler",
                "formatter": "file_format",
                "level": level,
                "filename": log_path,
                "when": "midnight",
                "interval": 1,
                "backupCount": backup_count,
                "encoding": "utf-8",
                "utc": True,
            },
        },
        "root": {
            "level": level,
            "handlers": ["console", "file"],
        },
    }

    logging.config.dictConfig(logging_config)
    
    logging.captureWarnings(True)

    def _excepthook(exc_type, exc_value, exc_tb):
        """
        Global exception hook to catch unhandled errors.
        """
        logger = logging.getLogger("uncaught")
        if exc_value is None:
            return
        logger.critical("Uncaught exception", exc_info=(exc_type, exc_value, exc_tb))

    sys.excepthook = _excepthook

    silenced_libraries = {
        "discord": "INFO",
        "discord.client": "ERROR",
        "discord.ext.commands.bot": "ERROR",
        "asyncio": "WARNING",
        "httpx": "WARNING",
        "azure": "WARNING",
        "azure.core.pipeline.policies.http_logging_policy": "WARNING",
    }

    if library_levels:
        silenced_libraries.update(library_levels)

    # Apply levels dynamically
    for library, log_level in silenced_libraries.items():
        logging.getLogger(library).setLevel(log_level)