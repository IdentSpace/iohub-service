"""Deliver scanner events away from the serial reader threads."""

from __future__ import annotations

import logging
import queue
import threading
import time
from urllib.parse import urlsplit

import requests
from sqlmodel import select

from app.db.models import SysValues
from app.db.session import get_session

logger = logging.getLogger(__name__)

_jobs: queue.Queue[tuple[str, str] | None] = queue.Queue(maxsize=500)
_worker: threading.Thread | None = None
_worker_lock = threading.Lock()
_STOP = None


def start_webhook_worker() -> None:
	global _worker
	with _worker_lock:
		if _worker is not None and _worker.is_alive():
			return
		_worker = threading.Thread(target=_deliver, name="webhook-worker", daemon=True)
		_worker.start()
		logger.info("Webhook worker started (queue capacity=%s)", _jobs.maxsize)


def stop_webhook_worker(timeout: float = 5.0) -> None:
	worker = _worker
	if worker is None or not worker.is_alive():
		return
	try:
		_jobs.put(_STOP, timeout=timeout)
		worker.join(timeout=timeout)
		if worker.is_alive():
			logger.warning("Webhook worker did not stop within %.1f seconds", timeout)
		else:
			logger.info("Webhook worker stopped")
	except queue.Full:
		logger.warning("Webhook queue is full; worker shutdown signal was not queued")


def enqueue_webhook(config_name: str, query: str) -> bool:
	"""Queue a configured webhook; never wait for network I/O in a device thread."""
	start_webhook_worker()
	try:
		_jobs.put_nowait((config_name, query))
		return True
	except queue.Full:
		logger.error("Webhook queue full; dropping event (config=%s)", config_name)
		return False


def _deliver() -> None:
	while True:
		job = _jobs.get()
		try:
			if job is _STOP:
				return
			config_name, query = job
			_started = time.monotonic()
			try:
				with get_session() as session:
					setting = session.exec(
						select(SysValues).where(SysValues.name == config_name)
					).first()
					base_url = setting.value if setting else None
				if not base_url:
					logger.warning("Webhook is not configured (config=%s)", config_name)
					continue
				parts = urlsplit(base_url)
				if parts.scheme not in ("http", "https") or not parts.netloc:
					logger.error("Invalid webhook URL (config=%s)", config_name)
					continue
				response = requests.get(base_url + query, timeout=(2, 5), headers={"Connection": "close"})
				logger.info(
					"Webhook delivered (config=%s status=%s elapsed_ms=%.1f)",
					config_name, response.status_code, (time.monotonic() - _started) * 1000,
				)
			except Exception:
				logger.exception(
					"Webhook delivery failed (config=%s elapsed_ms=%.1f)",
					config_name, (time.monotonic() - _started) * 1000,
				)
		finally:
			_jobs.task_done()
