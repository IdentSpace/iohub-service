"""Export the service API without initializing its database or background jobs."""
import argparse
import json
from pathlib import Path

from app.api.application import create_api


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("openapi.json"))
    args = parser.parse_args()
    schema = create_api().openapi()
    args.output.write_text(json.dumps(schema, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Exported {len(schema['paths'])} paths to {args.output.resolve()}")


if __name__ == "__main__":
    main()
