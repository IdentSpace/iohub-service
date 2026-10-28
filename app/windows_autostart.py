"""Per-user Windows logon startup registration for IOHub Service."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
SETTINGS_KEY = r"Software\IOHub Service\Settings"
VALUE_NAME = "IOHub Service"
DISABLED_VALUE_NAME = "AutostartDisabled"


def _startup_command() -> str:
	if getattr(sys, "frozen", False):
		command = [sys.executable]
	else:
		entry_point = Path(__file__).resolve().parents[1] / "run.build.py"
		command = [sys.executable, str(entry_point)]
	return subprocess.list2cmdline(command)


def is_autostart_enabled() -> bool:
	if sys.platform != "win32":
		return False
	import winreg

	try:
		with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_QUERY_VALUE) as key:
			value, _ = winreg.QueryValueEx(key, VALUE_NAME)
		return value == _startup_command()
	except FileNotFoundError:
		return False


def is_autostart_disabled_by_user() -> bool:
	if sys.platform != "win32":
		return False
	import winreg

	try:
		with winreg.OpenKey(winreg.HKEY_CURRENT_USER, SETTINGS_KEY, 0, winreg.KEY_QUERY_VALUE) as key:
			value, _ = winreg.QueryValueEx(key, DISABLED_VALUE_NAME)
		return value == 1
	except FileNotFoundError:
		return False


def set_autostart_enabled(enabled: bool = True) -> None:
	if sys.platform != "win32":
		raise OSError("Windows autostart is only available on Windows")
	import winreg

	with winreg.CreateKeyEx(
		winreg.HKEY_CURRENT_USER,
		RUN_KEY,
		0,
		winreg.KEY_SET_VALUE | winreg.KEY_QUERY_VALUE,
	) as key:
		if enabled:
			winreg.SetValueEx(key, VALUE_NAME, 0, winreg.REG_SZ, _startup_command())
		else:
			try:
				winreg.DeleteValue(key, VALUE_NAME)
			except FileNotFoundError:
				pass

	with winreg.CreateKeyEx(
		winreg.HKEY_CURRENT_USER,
		SETTINGS_KEY,
		0,
		winreg.KEY_SET_VALUE | winreg.KEY_QUERY_VALUE,
	) as key:
		if enabled:
			try:
				winreg.DeleteValue(key, DISABLED_VALUE_NAME)
			except FileNotFoundError:
				pass
		else:
			winreg.SetValueEx(key, DISABLED_VALUE_NAME, 0, winreg.REG_DWORD, 1)
