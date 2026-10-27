import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path


def configure_logging() -> Path:
	"""Configure console and rotating file logs; LOG_FILE can override the path."""
	log_path = Path(os.getenv("LOG_FILE", "logs/iohub-service.log"))
	log_path.parent.mkdir(parents=True, exist_ok=True)
	formatter = logging.Formatter(
		"%(asctime)s %(levelname)s [%(threadName)s] %(name)s: %(message)s"
	)
	file_handler = RotatingFileHandler(
		log_path, maxBytes=10 * 1024 * 1024, backupCount=5, encoding="utf-8"
	)
	file_handler.setFormatter(formatter)
	console_handler = logging.StreamHandler()
	console_handler.setFormatter(formatter)
	logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO").upper(), handlers=[file_handler, console_handler], force=True)
	return log_path
