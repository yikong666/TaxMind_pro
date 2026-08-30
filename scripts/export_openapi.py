from __future__ import annotations

import json
from pathlib import Path

from taxmind.entrypoints.api.main import create_app


def main() -> None:
    repository_root = Path(__file__).resolve().parents[1]
    output_path = repository_root / "packages/contracts/openapi/taxmind-v1.openapi.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    schema = create_app().openapi()
    output_path.write_text(
        json.dumps(schema, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"OpenAPI exported to {output_path}")


if __name__ == "__main__":
    main()