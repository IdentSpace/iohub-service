# Treibervertrag und Kompatibilität

Alle konkreten Treiber erben von `DeviceBase` und implementieren:

- `start()`: wiederholbarer Start ohne zusätzliche Reader-Threads.
- `close()`: wiederholbares Freigeben der Ressourcen; Reader warten höchstens drei Sekunden auf ihren Thread und melden einen Fehler, wenn er weiterläuft.
- `get_state() -> DeviceState`.
- `execute_command(cmd, arg=None) -> CommandResult`: unbekannte Befehle lösen `UnsupportedCommandError` aus, ungültige Argumente `ValueError`.
- `raw_command()`: bestehender Vertrag bleibt erhalten.

Gerätespezifische Fähigkeiten wie `ParkingBarrier` bleiben zusätzliche Schnittstellen.
`web_command()` bleibt als Weiterleitung auf `execute_command()` verfügbar. Dessen Rückgabe ist jetzt `CommandResult`; eigene Python-Aufrufer müssen gegebenenfalls angepasst werden.

`runtime_devices` in `app/devices/device_manager.py` verwaltet Instanzen pro normalisierter Geräte-UUID. API und Startup teilen diese Instanzen. Updates und Löschen schließen die bisherige Instanz; beim nächsten Zugriff wird die aktuelle Konfiguration geladen. Der Restart-Endpunkt schließt alle Instanzen und startet die konfigurierten seriellen Geräte erneut.

Es gibt keine Datenbankmigration. Bestehende Treibernamen, Hosts, Baudraten, Kanäle und API-Routen bleiben gültig. `device_host` wird in der Factory zusätzlich auf `port` abgebildet.

Hinweise für eigene Erweiterungen:

- Eigene `DeviceBase`-Unterklassen müssen die neuen abstrakten Methoden implementieren.
- Serielle Konstruktoren erwerben keine Hardware mehr. Direkte Python-Aufrufer müssen vor der Hardwarebenutzung `start()` beziehungsweise die bestehende Verbindungsmethode aufrufen.
- Unbekannte Befehle und fehlgeschlagene Schaltvorgänge ergeben eine API-Fehlerantwort statt einer scheinbaren Erfolgsmeldung.
- Der Manager gilt pro Prozess. Mehrere Server-Worker dürfen nicht dieselben seriellen Geräte betreiben.

Prüfung ohne Hardware:

    python -m unittest discover -s test -p test_driver_contract.py
    python -m unittest discover -s test -p test_dummy*.py



Befehle werden zentral in `types/commands.py` definiert:
`DeviceCommand.SWITCH`, `.OPEN`, `.CLOSE` sowie
`CommandArgument.ON` und `.OFF`. Der DeviceManager wandelt die bisherigen
API-Strings vor dem Aufruf des Treibers in diese Enums um und lehnt
unbekannte Werte ab. Beispiel:

    driver.execute_command(DeviceCommand.SWITCH, CommandArgument.ON)

Die Enum-Werte bleiben `switch`, `open`, `close`, `on` und `off`.


## Device types and reader events

NFC drivers inherit `NfcReader`, scanners inherit `DataScanner`. Both inherit
`ReaderBase`, which provides idempotent start/close and thread-safe
`subscribe(callback)` / `unsubscribe(callback)`. NFC callbacks receive `NfcData`,
scanner callbacks receive `DataScannerData`. The configured device ID is attached
by the publisher. Subscriber failures are logged independently so remaining
subscribers still receive the event. Callbacks execute on the reader thread and
must return quickly. Unsubscribe prevents future publications from selecting a
callback; a delivery already in progress may still finish.

For compatibility, the existing State/Webhook sink is installed when a reader
is constructed, including for direct Python users. It can later be moved to
application wiring when direct-user compatibility is retired. Transport-specific
connect/read behavior remains in the concrete drivers. Camera inherits DeviceBase
and requires `snapshot() -> bytes` (one JPEG image) and
`stream() -> Iterator[bytes]` (JPEG frames without HTTP multipart boundaries).
Camera drivers release stream resources when the iterator is closed and stop
active streams on `close()`. They advertise the `camera` capability.
Heater remains an independent interface. Shelly now implements Switch.

### Local USB and notebook cameras

Install the optional dependency with
`python -m pip install -r requirements-camera.txt`. The `local_camera` driver
loads OpenCV only on `start()`. `device_host` selects a camera index (`"0"`
for the first camera) or a device path such as `/dev/video0` on the IOHub host.
Driver arguments accept optional positive integer `width` and `height`,
positive `fps` (default 15) and `timeout` (default 5 seconds). Resolution and
hardware FPS are requests; actual support depends on the camera/backend.
These extra options are currently available through direct driver arguments;
the database configuration supplies `device_host` and uses the defaults.

    camera = driver_factory("local_camera", args={"device_host": "0"})
    camera.start()
    try:
        jpeg = camera.snapshot()
    finally:
        camera.close()

One capture thread reads and JPEG-encodes frames for all consumers. Snapshots
use the latest fresh frame; streams wait for new frames and may skip frames
for slow clients. Closing a stream leaves the shared capture running.
The existing `/api/v2/devices/{id}/snapshot` and `/stream` routes support this
driver. Frame waits time out; capture failures clear the cached image and
require a driver restart. Camera access permissions must permit the service
account to open the device.

`close()` wakes frame consumers and waits up to three seconds for capture to
stop. Some native camera backends can block in open/read; if so, `close()`
raises rather than claiming the camera has stopped. The capture thread releases
the device when that native call returns, and a new capture cannot start while
the old thread is still alive.

### Hanwha SUNAPI

`hanwha_http` constructs a `Hanwha` camera driver. Its `args` accept
`device_host` (hostname/IP, optionally with HTTP/HTTPS scheme and port),
`username` (default `admin`), `password`, `channel` (default 0), and
`timeout` (positive seconds, default 5). Authentication uses HTTP Digest.
Credentials must currently be passed in driver arguments; this change does
not add database fields or API routes for camera configuration or images.

`snapshot()` fetches `/stw-cgi/video.cgi?msubmenu=snapshot&action=view`;
`stream()` fetches the same path with `msubmenu=stream`. Both pass `Channel`.
The stream endpoint must deliver MJPEG; the driver yields individual JPEGs.
Closing the iterator releases its HTTP response. `close()` stops all active
streams; `start()` permits subsequent requests. No connection is opened by
the constructor or `start()`. State reflects the last request/frame, rather
than polling the camera. Network reads have a finite timeout.

Reader capabilities are inherited from their corresponding device type rather
than repeated in individual drivers. Contract tests verify that advertised NFC,
scanner, switch and barrier capabilities agree with inheritance.

CPR0210 still has no implemented UID decoding/event publication. Raw protocol
frames are deliberately not treated as UIDs. This pre-existing hardware protocol
limitation is not resolved by implementing the event interface.

Custom readers inherit additional abstract methods from DeviceBase through
ReaderBase, initialize their event source, and publish typed events. Existing
listen/listen_in_thread methods remain available. HoptSchuler events now include
the configured device ID, consistent with other NFC readers.
