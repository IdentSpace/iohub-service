import logging
import os
import sys
from copy import copy
from logging.handlers import RotatingFileHandler
from pathlib import Path


class _ApplicationFormatter(logging.Formatter):
	"""Use a neutral display name for Uvicorn's server status logger."""

	def format(self, record: logging.LogRecord) -> str:
		if record.name == "uvicorn.error":
			record = copy(record)
			record.name = "uvicorn"
		return super().format(record)


def configure_logging() -> Path:
	"""Configure console and rotating file logs; LOG_FILE can override the path."""
	configured_path = os.getenv("LOG_FILE")
	if configured_path:
		log_path = Path(configured_path)
	elif os.name == "nt" and getattr(sys, "frozen", False):
		app_data = Path(os.getenv("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
		log_path = app_data / "IOHub Service" / "logs" / "iohub-service.log"
	else:
		log_path = Path("logs/iohub-service.log")
	log_path.parent.mkdir(parents=True, exist_ok=True)
	formatter = _ApplicationFormatter(
		"%(asctime)s %(levelname)s [%(threadName)s] %(name)s: %(message)s"
	)
	file_handler = RotatingFileHandler(
		log_path, maxBytes=10 * 1024 * 1024, backupCount=5, encoding="utf-8"
	)
	file_handler.setFormatter(formatter)
	handlers = [file_handler]
	if sys.stderr is not None:
		console_handler = logging.StreamHandler(sys.stderr)
		console_handler.setFormatter(formatter)
		handlers.append(console_handler)
	logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO").upper(), handlers=handlers, force=True)
	return log_path
