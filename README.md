# IOHub Service

!!! Fresh and under development

- IOHub Service manages IP and serial devices such as Shelly devices and scanners.
- Other applications can integrate through the HTTP API.

## Tested Driver

| Device | Connection | Usage |
|---|---|---|
| Shelly PM | Network | IoT |
| Datascanner | Serial | Barcodes / Datamatrix |
| Automatic Systems AS1620 | Network | Parking Barrier |

## Install

Global installation of packages:

```sh
pip3 install -r requirements.txt
```

Local environment:

```sh
python3 -m venv venv
source venv/bin/activate
```

## Run

```sh
systemctl start iot-hub-core
python ./run.py
```

## Demo data

Generate 16 demo devices (two of each supported type) from the repository root:

```sh
python generate_demo_data.py
```

Includes base devices, lamps, workshop machines, doors, heaters, barcode scanners,
NFC readers, and parking barriers with matching driver configurations. Dependencies
from `requirements.txt` must be installed. Existing data is preserved; repeated runs
skip demo devices already present. Increasing `--per-type` adds more devices.

```sh
python generate_demo_data.py --per-type 5 --db demo.db
```

The default database is `data.db` in the current working directory, as with source
runs of IOHub. For the installed Windows client, pass
`--db "$env:LOCALAPPDATA\IOHub Service\data.db"` in PowerShell while IOHub is stopped.
A separate `demo.db` is only used by this script and is not automatically selected
by the application. These are configuration examples, without simulated live states.
Network addresses use `.invalid`; serial placeholders avoid automatic serial
listeners. The script does not contact hardware or create users or credentials.

### Simulated serial scanner

```sh
python generate_demo_data.py --dummy
```

This also creates a `Demo COM Scanner` using the `dummy_datascanner` driver and
`dummy://datascanner/COM-DEMO-1?interval=3`. Restart IOHub or call
`GET /api/config/restart/threads` once to activate it. Every three seconds it
alternates raw barcode and GS1 Datamatrix lines through the existing serial scanner
parser, latest-scan storage, and `WEBHOOK_DATASCANNER` delivery. Configured scanner
webhooks therefore receive these demo events too.

Inspect the latest scan without consuming it at `GET /api/device/scanner/latest`.
The `id` identifies the emitting scanner; before any scan arrives, `scan` is null.
This is the most recent scan across all scanners, not an event history.
Change the URL's `interval` query parameter (seconds, minimum 0.01) and restart
device threads to change the frequency. Delete the dummy device and restart threads
to stop simulation. This simulates the serial connection inside IOHub; it does not
create an operating-system COM port. Other demo devices remain placeholders.

### Simulated NFC reader

```sh
python generate_demo_data.py --dummy-nfc
```

Creates one repeatable `Demo NFC Reader` with driver `dummy_nfcreader` at
`dummy://nfcreader/COM-DEMO-1?interval=3`. Restart IOHub or its device threads to
activate it. It cycles three demo card UIDs every three seconds through the normal
NFC reader pipeline, including `WEBHOOK_NFC` and `/auth/wait-for-card`.
`GET /api/device/nfc/latest` returns the latest card without consuming it (or null
before a card arrives); `deviceId` identifies its reader. Like the scanner dummy,
it runs inside IOHub without creating an operating-system COM port.

## Build Windows Client

Install the dependencies and build the tray application from the repository root:

```powershell
python -m pip install -r requirements.txt
python -m pip install pyinstaller
python -m PyInstaller --clean --noconfirm run.build.spec
```

The build is written to `dist/IOHub Service/`. Launch `IOHub Service.exe` to start the API in the background. On first launch, IOHub registers itself for the current user's Windows sign-in unless autostart was previously removed. The tray menu includes **Autostart beim Anmelden einrichten** and **Autostart entfernen**. A Windows mutex prevents a second tray process from starting with the same `APP_HOST` and `APP_PORT`; a different pair can run separately. The tray menu opens the API documentation or a live PowerShell log terminal. Choose **IOHub beenden** to stop the service cleanly. Logs and the SQLite database are stored under `%LOCALAPPDATA%\IOHub Service`; the database file is `data.db`. In source runs, `data.db` is created in the current working directory.

To archive the current log and start IOHub with a new empty log, run this in PowerShell while IOHub is stopped:

```powershell
& ".\IOHub Service.exe" --new-log
```

The previous log is retained beside the new log with a timestamp in its filename.

## Milestones

1. Control different device types with Shellys over HTTP
2. Rolls and cans
3. Shelly WebSocket support
4. Support for additional IoT brands and device types
5. Implement hooks
6. Watch and sync

## Shortcuts

```sh
lsusb
lsusb -d <usbvendorpid> -v

systemctl status iot-hub-core
journalctl -u iot-hub-core -f

# List serial devices
ls /dev/tty[A-Z]*
```

## Maintainer

IdentSpace

## Partners

2G Konzept DudoPark
# OpenAPI export

Export the current API without starting the service, database initialization,
or background jobs:

```sh
python export_openapi.py
```

The output is `openapi.json`; use `--output path/to/openapi.json` for another
location. A running service also serves the schema at `/openapi.json` and
interactive documentation at `/docs`.

