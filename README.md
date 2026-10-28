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

## Build Windows Client

Install the dependencies and build the tray application from the repository root:

```powershell
python -m pip install -r requirements.txt
python -m pip install pyinstaller
python -m PyInstaller --clean --noconfirm run.build.spec
```

The build is written to `dist/IOHub Service/`. Launch `IOHub Service.exe` to start the API in the background. On first launch, IOHub registers itself for the current user's Windows sign-in unless autostart was previously removed. The tray menu includes **Autostart beim Anmelden einrichten** and **Autostart entfernen**. A Windows mutex prevents a second tray process from starting with the same `APP_HOST` and `APP_PORT`; a different pair can run separately. The tray menu opens the API documentation or a live PowerShell log terminal. Choose **IOHub beenden** to stop the service cleanly. Logs and the SQLite database are stored under `%LOCALAPPDATA%\IOHub Service`; the database file is `data.db`. In source runs, `data.db` is created in the current working directory.

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
