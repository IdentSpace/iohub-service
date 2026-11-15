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
