# Simons Voss
# SREL3.EXT.G2.W.WP
"""Passiver RS485-Empfangstest; keine Protokollimplementierung.

Aufruf:
    python test/test_simonvoss.py --list-ports
    python test/test_simonvoss.py --port COM8

1 MBaud ist dokumentiert; 8N1 ist eine unbestaetigte Testannahme.
Ausgegebene Bloecke sind Empfangsabschnitte, keine erkannten Telegramme.
"""

import argparse
from datetime import datetime

import serial
from serial.tools import list_ports


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--list-ports", action="store_true", help="COM-Ports anzeigen")
    parser.add_argument("--port", help="Serieller Port, z.B. COM8")
    parser.add_argument("--baudrate", type=int, default=1_000_000)
    parser.add_argument("--bytesize", type=int, choices=(7, 8), default=8)
    parser.add_argument("--parity", choices=("N", "E", "O"), default="N")
    parser.add_argument("--stopbits", type=int, choices=(1, 2), default=1)
    args = parser.parse_args()

    if args.list_ports:
        ports = list(list_ports.comports())
        for port in ports:
            print(f"{port.device}: {port.description}")
        if not ports:
            print("Keine seriellen Ports gefunden.")
        return 0

    if not args.port:
        parser.error("--port fehlt. Verfuegbare Ports mit --list-ports anzeigen.")
    if args.baudrate <= 0:
        parser.error("--baudrate muss positiv sein.")

    total = 0
    try:
        with serial.Serial(
            port=args.port,
            baudrate=args.baudrate,
            bytesize=args.bytesize,
            parity=args.parity,
            stopbits=args.stopbits,
            timeout=0.1,
            xonxoff=False,
            rtscts=False,
            dsrdtr=False,
        ) as connection:
            print(
                f"Empfange auf {args.port}: {args.baudrate} Baud, "
                f"{args.bytesize}{args.parity}{args.stopbits}. Abbruch: Strg+C.",
                flush=True,
            )
            print(
                "Keine Sendebefehle. Keine Ausgabe bedeutet nur: keine Bytes empfangen.\n"
                "Der Leser wartet eventuell auf einen Controller. "
                "Jetzt Karte vorhalten oder Leser einschalten.",
                flush=True,
            )
            while True:
                data = connection.read(1)
                if not data:
                    continue
                data += connection.read(min(connection.in_waiting, 4095))
                total += len(data)
                timestamp = datetime.now().astimezone().isoformat(timespec="milliseconds")
                print(f"{timestamp}  RX {len(data):4d} Bytes  {data.hex(' ').upper()}", flush=True)
    except KeyboardInterrupt:
        print(f"\nBeendet. Insgesamt {total} Bytes empfangen.")
        return 0
    except (serial.SerialException, OSError, ValueError) as error:
        print(f"Serieller Fehler: {error}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
