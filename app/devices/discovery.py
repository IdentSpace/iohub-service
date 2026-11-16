"""Discover hardware attached to the IOHub server, not the browser client."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

from serial.tools import list_ports


def serial_devices():
    return [{"host": port.device, "description": port.description,
             "manufacturer": port.manufacturer, "serial_number": port.serial_number,
             "vid": port.vid, "pid": port.pid}
            for port in sorted(list_ports.comports(), key=lambda item: item.device)]


_PROBE = """
import cv2, json, sys
source = json.loads(sys.argv[1])
capture = cv2.VideoCapture(source)
try:
    ok, frame = capture.read() if capture.isOpened() else (False, None)
    print('IOHUB_PROBE=' + json.dumps(bool(ok and frame is not None)))
finally:
    capture.release()
"""


def camera_devices(max_index=4):
    if importlib.util.find_spec("cv2") is None:
        return {"available": False, "items": [], "issues": [],
                "message": "Install camera support: python -m pip install -r requirements-camera.txt"}
    # Linux device paths avoid probing nonexistent indices and are usable hosts.
    sources = ([str(path) for path in sorted(Path("/dev").glob("video*"))]
               if sys.platform.startswith("linux") else list(range(max_index + 1)))
    items, issues = [], []
    for source in sources:
        try:
            result = subprocess.run([sys.executable, "-c", _PROBE, json.dumps(source)],
                                    capture_output=True, text=True, timeout=3)
            if result.returncode == 0 and "IOHUB_PROBE=true" in result.stdout.splitlines():
                items.append({"host": str(source), "description": f"Local camera {source}",
                              "driver": "local_camera"})
            else:
                issues.append({"host": str(source), "reason": "unavailable_or_unreadable"})
        except subprocess.TimeoutExpired:
            issues.append({"host": str(source), "reason": "probe_timeout"})
        except OSError:
            issues.append({"host": str(source), "reason": "probe_failed"})
    return {"available": True, "items": items, "issues": issues,
            "message": "Only cameras delivering frames are listed. Busy cameras may be unavailable."}
