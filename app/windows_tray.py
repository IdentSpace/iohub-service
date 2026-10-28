from __future__ import annotations

import ctypes
import logging
import os
import subprocess
import threading
import time
import urllib.error
import urllib.request
import webbrowser

import pystray
import uvicorn
from PIL import Image

from app.main import app, log_path
from app.core.utils import get_resource_path
from app.windows_autostart import set_autostart_enabled

logger = logging.getLogger(__name__)


def _make_icon() -> Image.Image:
	with Image.open(get_resource_path("app/assets/iohub.ico")) as icon:
		return icon.convert("RGBA").resize((64, 64), Image.Resampling.LANCZOS)


class IOHubTray:
	def __init__(self) -> None:
		self.host = os.getenv("APP_HOST", "0.0.0.0").strip()
		self.port = int(os.getenv("APP_PORT", "8005"))
		# GoSign can occupy 127.0.0.1:8000 while IOHub listens on all interfaces.
		browser_host = "127.0.0.2" if self.host in ("", "0.0.0.0") else self.host
		if ":" in browser_host and not browser_host.startswith("["):
			browser_host = f"[{browser_host}]"
		self.url = f"http://{browser_host}:{self.port}"
		self._server: uvicorn.Server | None = None
		self._server_thread: threading.Thread | None = None
		self._server_lock = threading.Lock()
		self._restart_requested = False
		self.icon = pystray.Icon(
			"iohub-service",
			_make_icon(),
			"IOHub Service",
			menu=pystray.Menu(
				pystray.MenuItem("API-Dokumentation öffnen", self.open_api),
				pystray.MenuItem("Live-Log-Terminal öffnen", self.open_log_terminal, default=True),
				pystray.MenuItem("Autostart beim Anmelden einrichten", self.setup_autostart),
				pystray.MenuItem("Autostart entfernen", self.remove_autostart),
				pystray.MenuItem("IOHub neu starten", self.restart),
				pystray.Menu.SEPARATOR,
				pystray.MenuItem("IOHub beenden", self.exit),
			),
		)

	def start_server(self) -> bool:
		with self._server_lock:
			if self._server_thread and self._server_thread.is_alive():
				return bool(self._server and self._server.started)
		config = uvicorn.Config(
			app,
			host=self.host or "0.0.0.0",
			port=self.port,
			log_config=None,
			access_log=False,
		)
		self._server = uvicorn.Server(config)
		self._server.install_signal_handlers = lambda: None
		self._server_thread = threading.Thread(
			target=self._run_server,
			name="iohub-api-server",
			daemon=False,
		)
		self._server_thread.start()
		deadline = time.monotonic() + 15
		while self._server_thread.is_alive() and not self._server.started and time.monotonic() < deadline:
			time.sleep(0.1)
		if self._server.started:
			logger.info("IOHub API server ready at %s", self.url)
			return True
		if self._server_thread.is_alive():
			self._server.should_exit = True
			self._server_thread.join(timeout=5)
		logger.error("IOHub API server did not start on %s:%s", self.host or "0.0.0.0", self.port)
		return False

	def _run_server(self) -> None:
		try:
			if self._server is not None:
				self._server.run()
		except Exception:
			logger.exception("IOHub API server crashed during startup or while running")

	def open_api(self, _icon: pystray.Icon, _item: pystray.MenuItem) -> None:
		if self._server and self._server.started:
			webbrowser.open(f"{self.url}/docs")
		else:
			self._show_start_error()

	def _existing_api_responds(self) -> bool:
		try:
			with urllib.request.urlopen(f"{self.url}/health", timeout=2) as response:
				return response.status == 200
		except (OSError, urllib.error.URLError):
			return False

	def _show_start_error(self) -> None:
		if os.name == "nt":
			ctypes.windll.user32.MessageBoxW(
				None,
				f"IOHub konnte nicht unter {self.host or '0.0.0.0'}:{self.port} starten. "
				f"Das Tray-Symbol bleibt aktiv. Öffne dort das Live-Log-Terminal für Details.\n\n"
				f"Logdatei: {log_path.resolve()}",
				"IOHub Service nicht gestartet",
				0x10,
			)

	def open_log_terminal(self, _icon: pystray.Icon, _item: pystray.MenuItem) -> None:
		if os.name != "nt":
			logger.warning("Live log terminal is available only on Windows")
			return
		log_file = str(log_path.resolve()).replace("'", "''")
		command = (
			f"$log = '{log_file}'; "
			"Write-Host 'IOHub Live-Logs (Strg+C beendet die Anzeige)'; "
			"Get-Content -LiteralPath $log -Tail 100 -Wait"
		)
		try:
			subprocess.Popen(
				["powershell.exe", "-NoExit", "-Command", command],
				creationflags=subprocess.CREATE_NEW_CONSOLE,
			)
		except OSError:
			logger.exception("Could not open the live log terminal")

	def exit(self, icon: pystray.Icon, _item: pystray.MenuItem) -> None:
		icon.stop()

	def restart(self, icon: pystray.Icon, _item: pystray.MenuItem) -> None:
		logger.info("IOHub restart requested from tray")
		self._restart_requested = True
		icon.stop()

	def setup_autostart(self, _icon: pystray.Icon, _item: pystray.MenuItem) -> None:
		try:
			set_autostart_enabled()
			logger.info("IOHub Service is registered to start when the current user signs in")
		except OSError:
			logger.exception("Could not register IOHub Service in Windows autostart")
			if os.name == "nt":
				ctypes.windll.user32.MessageBoxW(
					None,
					"Der IOHub-Autostart konnte nicht eingerichtet werden. Details stehen im Log.",
					"IOHub Autostart",
					0x10,
				)

	def remove_autostart(self, _icon: pystray.Icon, _item: pystray.MenuItem) -> None:
		try:
			set_autostart_enabled(False)
			logger.info("IOHub Service was removed from Windows autostart")
		except OSError:
			logger.exception("Could not remove IOHub Service from Windows autostart")
			if os.name == "nt":
				ctypes.windll.user32.MessageBoxW(
					None,
					"Der IOHub-Autostart konnte nicht entfernt werden. Details stehen im Log.",
					"IOHub Autostart",
					0x10,
				)

	def run(self) -> bool:
		if not self.start_server():
			if self._existing_api_responds():
				logger.warning("An IOHub API is already responding at %s; opening it", self.url)
				webbrowser.open(f"{self.url}/docs")
			else:
				self._show_start_error()
		try:
			self.icon.run()
		finally:
			shutdown_complete = self.stop_server()
		return self._restart_requested and shutdown_complete

	def stop_server(self) -> bool:
		with self._server_lock:
			server = self._server
			thread = self._server_thread
			if server is None or thread is None or not thread.is_alive():
				return True
			logger.info("Stopping IOHub API server")
			server.should_exit = True
		thread.join(timeout=20)
		if thread.is_alive():
			logger.error("IOHub API server did not stop within 20 seconds")
			return False
		else:
			logger.info("IOHub API server stopped")
			return True


def run_tray() -> bool:
	if os.name != "nt":
		raise RuntimeError("The IOHub tray application is intended for Windows")
	return IOHubTray().run()
