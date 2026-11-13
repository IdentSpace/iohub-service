"""Windows tray entry point for the IOHub Service desktop build."""

import ctypes
from datetime import datetime
import hashlib
import os
from pathlib import Path
import subprocess
import sys

from dotenv import load_dotenv


def start_with_clean_log() -> Path:
	"""Archive the current log so the application creates a fresh one on startup."""
	configured_path = os.getenv("LOG_FILE")
	if configured_path:
		log_path = Path(configured_path)
	elif getattr(sys, "frozen", False):
		app_data = Path(os.getenv("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
		log_path = app_data / "IOHub Service" / "logs" / "iohub-service.log"
	else:
		log_path = Path("logs/iohub-service.log")

	if log_path.is_file():
		stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
		archive_path = log_path.with_name(f"{log_path.stem}-{stamp}{log_path.suffix}")
		log_path.replace(archive_path)
		return archive_path
	return log_path


def acquire_instance_mutex() -> int | None:
	"""Keep one tray process per configured host/port pair on Windows."""
	app_dir = Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent
	load_dotenv(app_dir / ".env")
	host = os.getenv("APP_HOST", "0.0.0.0").strip().lower().rstrip(".")
	port = int(os.getenv("APP_PORT", "8005"))
	address = f"{host}:{port}"
	mutex_key = hashlib.sha256(address.encode("utf-8")).hexdigest()
	mutex_name = f"Local\\IOHubService-{mutex_key}"

	kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
	kernel32.CreateMutexW.argtypes = [ctypes.c_void_p, ctypes.c_bool, ctypes.c_wchar_p]
	kernel32.CreateMutexW.restype = ctypes.c_void_p
	kernel32.CloseHandle.argtypes = [ctypes.c_void_p]
	kernel32.CloseHandle.restype = ctypes.c_bool
	handle = kernel32.CreateMutexW(None, True, mutex_name)
	if not handle:
		raise ctypes.WinError(ctypes.get_last_error())

	if ctypes.get_last_error() == 183:  # ERROR_ALREADY_EXISTS
		kernel32.CloseHandle(handle)
		user32 = ctypes.WinDLL("user32", use_last_error=True)
		user32.MessageBoxW(
			None,
			f"IOHub Service läuft bereits für {address}.",
			"IOHub Service bereits gestartet",
			0x40,
		)
		return None

	return handle


if __name__ == "__main__":
	_instance_mutex = acquire_instance_mutex()
	if _instance_mutex is None:
		sys.exit(0)

	_new_log_requested = "--new-log" in sys.argv[1:]
	if _new_log_requested:
		try:
			start_with_clean_log()
		except OSError as error:
			kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
			kernel32.ReleaseMutex.argtypes = [ctypes.c_void_p]
			kernel32.ReleaseMutex.restype = ctypes.c_bool
			kernel32.CloseHandle.argtypes = [ctypes.c_void_p]
			kernel32.CloseHandle.restype = ctypes.c_bool
			kernel32.ReleaseMutex(_instance_mutex)
			kernel32.CloseHandle(_instance_mutex)
			ctypes.windll.user32.MessageBoxW(
				None,
				f"Das bisherige Log konnte nicht archiviert werden:\n{error}",
				"IOHub Log konnte nicht zurückgesetzt werden",
				0x10,
			)
			sys.exit(1)

	from app.windows_tray import run_tray
	from app.windows_autostart import is_autostart_disabled_by_user, is_autostart_enabled, set_autostart_enabled
	if not is_autostart_enabled() and not is_autostart_disabled_by_user():
		try:
			set_autostart_enabled()
		except OSError:
			import logging
			logging.getLogger(__name__).exception("Could not register IOHub Service in Windows autostart")

	if run_tray():
		kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
		kernel32.ReleaseMutex.argtypes = [ctypes.c_void_p]
		kernel32.ReleaseMutex.restype = ctypes.c_bool
		kernel32.CloseHandle.argtypes = [ctypes.c_void_p]
		kernel32.CloseHandle.restype = ctypes.c_bool
		kernel32.ReleaseMutex(_instance_mutex)
		kernel32.CloseHandle(_instance_mutex)
		restart_args = [arg for arg in sys.argv[1:] if arg != "--new-log"]
		command = [sys.executable, *restart_args] if getattr(sys, "frozen", False) else [sys.executable, sys.argv[0], *restart_args]
		try:
			subprocess.Popen(
				command,
				cwd=os.getcwd(),
				close_fds=True,
				creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP,
			)
		except OSError:
			import logging
			logging.getLogger(__name__).exception("Could not restart IOHub Service")
			ctypes.windll.user32.MessageBoxW(
				None,
				"IOHub wurde beendet, konnte aber nicht neu gestartet werden. Details stehen im Log.",
				"IOHub Neustart fehlgeschlagen",
				0x10,
			)
