import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

def setup_logging(log_level: str, log_file: str, werkzeug_log_level: str = "INFO") -> None:
    Path(log_file).parent.mkdir(parents=True, exist_ok=True)

    root = logging.getLogger()
    root.setLevel(log_level)

    fmt = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s:%(lineno)d | %(message)s"
    )

    console = logging.StreamHandler()
    console.setLevel(log_level)
    console.setFormatter(fmt)

    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=1_000_000,
        backupCount=3,
        encoding="utf-8",
    )
    file_handler.setLevel(log_level)
    file_handler.setFormatter(fmt)

    # Prevent duplicates on reload by replacing handlers
    root.handlers = [console, file_handler]

    # Reduce noisy request logs (dev server)
    logging.getLogger("werkzeug").setLevel(werkzeug_log_level)