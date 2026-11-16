#!/bin/bash
set -euo pipefail

# Absoluter Pfad zum aktuellen Ordner (wo install.sh liegt)
BASE_DIR="$(cd "$(dirname "$0")" && pwd)"

# Prüfen, ob der Benutzer root ist (für Systemd-Zugriff notwendig)
if [ "$EUID" -ne 0 ]; then
    echo "Bitte als root oder mit sudo ausführen."
    exit 1
fi

# Python3 und venv prüfen
if ! command -v python3 &> /dev/null; then
    echo "Python3 ist nicht installiert. Bitte installieren."
    exit 1
fi

if ! python3 -m venv --help &> /dev/null; then
    echo "Python venv-Modul fehlt. Bitte sicherstellen, dass python3-venv installiert ist."
    exit 1
fi

# Virtuelles Environment einrichten
echo "Richte Python venv in $BASE_DIR/venv ein..."
python3 -m venv "$BASE_DIR/venv"

# Aktivieren und Abhängigkeiten installieren, falls requirements.txt existiert
if [ -f "$BASE_DIR/requirements.txt" ]; then
    echo "Installiere Python-Abhängigkeiten aus requirements.txt..."
    source "$BASE_DIR/venv/bin/activate"
    pip install --upgrade pip
    pip install -r "$BASE_DIR/requirements.txt"
    deactivate
else
    echo "Keine requirements.txt gefunden, überspringe Installation von Abhängigkeiten."
fi

# Systemd-Service kopieren
SERVICE_FILE="$BASE_DIR/iohub.service"
if [ -f "$SERVICE_FILE" ]; then
    echo "Kopiere $SERVICE_FILE nach /etc/systemd/system/..."
    install -m 644 "$SERVICE_FILE" /etc/systemd/system/iohub.service
    # Match the unit paths to this installation directory.
    python3 - "$BASE_DIR" /etc/systemd/system/iohub.service <<'PY'
from pathlib import Path
import sys

base_dir = sys.argv[1]
if any(c in base_dir for c in '\n\r'):
    raise SystemExit("Installationspfad darf keine Zeilenumbrüche enthalten")
escaped = base_dir.replace('\\', '\\\\').replace('"', '\\"').replace('%', '%%')
unit = Path(sys.argv[2])
text = unit.read_text()
text = text.replace('WorkingDirectory=/opt/iohub-service', f'WorkingDirectory="{escaped}"')
exec_dir = escaped.replace('$', '$$')
text = text.replace('ExecStart=/opt/iohub-service/venv/bin/python3 run.py',
                    f'ExecStart="{exec_dir}/venv/bin/python3" run.py')
unit.write_text(text)
PY
    install -m 755 "$BASE_DIR/scripts/iohub" /usr/local/bin/iohub
    systemctl daemon-reload
    systemctl enable iohub.service
    echo "Service iohub.service wurde aktiviert. Start mit: iohub start"
    echo "Weitere Befehle: iohub -restart, iohub status, iohub logs, iohub help"
else
    echo "Service-Datei $SERVICE_FILE nicht gefunden."
    exit 1
fi
