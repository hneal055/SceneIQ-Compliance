New-Item -ItemType Directory -Force .\src,.\logs | Out-Null; @'
from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

_CONFIGURED = False

def setup_logging(level: str = "INFO") -> Path:
    global _CONFIGURED
    root = Path(__file__).resolve().parents[1]
    log_dir = root / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "server.log"

    if _CONFIGURED:
        return log_file

    fmt = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    datefmt = "%Y-%m-%d %H:%M:%S"

    root_logger = logging.getLogger()
    root_logger.setLevel(level.upper())

    # remove existing handlers to avoid reload duplicates
    for h in list(root_logger.handlers):
        root_logger.removeHandler(h)

    stream = logging.StreamHandler()
    stream.setFormatter(logging.Formatter(fmt=fmt, datefmt=datefmt))

    fileh = RotatingFileHandler(
        filename=str(log_file),
        maxBytes=10_000_000,
        backupCount=5,
        encoding="utf-8",
    )
    fileh.setFormatter(logging.Formatter(fmt=fmt, datefmt=datefmt))

    root_logger.addHandler(stream)
    root_logger.addHandler(fileh)

    # Make uvicorn loggers propagate to root so they land in server.log too
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        lg = logging.getLogger(name)
        lg.handlers = []
        lg.propagate = True
        lg.setLevel(level.upper())

    _CONFIGURED = True
    return log_file
'@ | Out-File -Encoding utf8 -NoNewline .\src\logging_setup.py

