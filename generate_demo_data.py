"""Generate repeatable demo device configurations without contacting hardware."""

import argparse
from datetime import datetime, timezone
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

from sqlalchemy import event
from sqlmodel import Session, SQLModel, create_engine, select

from app.db.models import Device, DeviceDriver, DeviceType


# Type, description, driver, driver description, display name, connection.
PROFILES = (
    ("base", "Allgemeines Gerät", "default", "Generic device", "Basisgerät", "network"),
    ("lamp", "Beleuchtung", "shelly_http", "Shelly devices via HTTP", "Lampe", "network"),
    ("machine", "Werkstattmaschine", "shelly_http", "Shelly devices via HTTP", "Maschine", "network"),
    ("door", "Türsteuerung", "shelly_http", "Shelly devices via HTTP", "Tür", "network"),
    ("heater", "Heizung", "shelly_http", "Shelly devices via HTTP", "Heizung", "network"),
    ("datascanner", "Barcode- und Datamatrix-Scanner", "default_datascanner", "Default Data Scanner 1D / 2D", "Barcode-Scanner", "serial"),
    ("nfcreader", "NFC-Leser", "default_nfcreader", "Default NFC Scanner", "NFC-Leser", "serial"),
    ("parking_barrier", "Parkplatzschranke", "as1620", "Parking Barrier from Automatic Systems", "Schranke", "network"),
)


def positive_int(value):
    number = int(value)
    if number < 1:
        raise argparse.ArgumentTypeError("Die Anzahl muss mindestens 1 sein.")
    return number


def generate_dummy_scanner(db_path: Path, kind="datascanner"):
    """Create one opt-in, repeatable simulated serial device."""
    if kind not in ("datascanner", "nfcreader"):
        raise ValueError("Unsupported dummy device type")
    label = "COM Scanner" if kind == "datascanner" else "NFC Reader"
    driver_name = f"dummy_{kind}"
    engine = create_engine("sqlite:///" + db_path.resolve().as_posix())
    try:
        SQLModel.metadata.create_all(engine)
        with Session(engine) as session:
            device_type = session.exec(select(DeviceType).where(DeviceType.name == kind)).first()
            if device_type is None:
                device_type = DeviceType(name=kind, description=label, created_at=datetime.now(timezone.utc))
                session.add(device_type)
            driver = session.exec(select(DeviceDriver).where(DeviceDriver.name == driver_name)).first()
            if driver is None:
                driver = DeviceDriver(name=driver_name, description=f"Simulated serial {label}", created_at=datetime.now(timezone.utc))
                session.add(driver)
            session.flush()
            device_id = uuid5(NAMESPACE_URL, f"iohub:demo:dummy-{kind}:1")
            if session.get(Device, device_id) is None:
                session.add(Device(
                    id=device_id, name=f"Demo {label}",
                    device_host=f"dummy://{kind}/COM-DEMO-1?interval=3",
                    device_type=str(device_type.id), device_driver=str(driver.id),
                    created_at=datetime.now(timezone.utc), updated_at=datetime.now(timezone.utc),
                ))
            session.commit()
            return device_id
    finally:
        engine.dispose()


def generate_demo_data(db_path: Path, per_type: int) -> tuple[int, int]:
    """Add missing demo devices atomically; preserve existing configurations."""
    engine = create_engine("sqlite:///" + db_path.resolve().as_posix())

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(connection, _):
        connection.execute("PRAGMA foreign_keys=ON")

    created = skipped = 0
    try:
        SQLModel.metadata.create_all(engine)
        with Session(engine) as session:
            for type_name, description, driver_name, driver_description, label, connection in PROFILES:
                device_type = session.exec(select(DeviceType).where(DeviceType.name == type_name)).first()
                if device_type is None:
                    device_type = DeviceType(name=type_name, description=description, created_at=datetime.now(timezone.utc))
                    session.add(device_type)
                driver = session.exec(select(DeviceDriver).where(DeviceDriver.name == driver_name)).first()
                if driver is None:
                    driver = DeviceDriver(name=driver_name, description=driver_description, created_at=datetime.now(timezone.utc))
                    session.add(driver)
                session.flush()

                for index in range(1, per_type + 1):
                    device_id = uuid5(NAMESPACE_URL, f"iohub:demo:{type_name}:{index}")
                    if session.get(Device, device_id) is not None:
                        skipped += 1
                        continue
                    # Serial placeholders intentionally do not match COM* or /dev/tty*:
                    # the application must not start listeners on real serial ports.
                    host = (
                        f"demo-serial://{type_name}/{index}"
                        if connection == "serial"
                        else f"demo-{type_name}-{index:03d}.invalid"
                    )
                    session.add(Device(
                        id=device_id,
                        name=f"Demo {label} {index:03d}",
                        device_host=host,
                        device_type=str(device_type.id),
                        device_driver=str(driver.id),
                        baudrate=19200,
                        channel=0,
                        created_at=datetime.now(timezone.utc),
                        updated_at=datetime.now(timezone.utc),
                    ))
                    created += 1
            session.commit()
    finally:
        engine.dispose()
    return created, skipped


def main():
    parser = argparse.ArgumentParser(description="Demo-Geräte für IOHub anlegen (ohne Hardwarezugriff).")
    parser.add_argument("--db", type=Path, default=Path("data.db"), help="SQLite-Datei (Standard: data.db im aktuellen Verzeichnis)")
    parser.add_argument("--per-type", type=positive_int, default=2, help="Geräte je Typ (Standard: 2)")
    parser.add_argument("--dummy", action="store_true", help="Zusätzlich einen simulierten COM-Scanner anlegen")
    parser.add_argument("--dummy-nfc", action="store_true", help="Zusätzlich einen simulierten NFC-Leser anlegen")
    args = parser.parse_args()
    if not args.db.resolve().parent.is_dir():
        parser.error("Das Zielverzeichnis der Datenbank existiert nicht.")
    created, skipped = generate_demo_data(args.db, args.per_type)
    print(f"Datenbank: {args.db.resolve()}")
    print(f"{created} Demo-Geräte angelegt, {skipped} bereits vorhanden ({len(PROFILES)} Gerätetypen).")
    print("Die Geräte sind Konfigurationsbeispiele; Live-Zustände benötigen echte Hardware.")
    if args.dummy:
        device_id = generate_dummy_scanner(args.db)
        print(f"Dummy COM-Scanner bereit: {device_id} (Intervall: 3 Sekunden).")
        print("Zum Aktivieren IOHub bzw. die Gerätethreads neu starten.")
    if args.dummy_nfc:
        device_id = generate_dummy_scanner(args.db, kind="nfcreader")
        print(f"Dummy NFC-Reader bereit: {device_id} (Intervall: 3 Sekunden).")
        print("Zum Aktivieren IOHub bzw. die Gerätethreads neu starten.")


if __name__ == "__main__":
    main()
