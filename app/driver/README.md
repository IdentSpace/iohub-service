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
connect/read behavior remains in the concrete drivers. Camera is still a stub;
Heater remains an independent interface. Shelly now implements Switch.

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
