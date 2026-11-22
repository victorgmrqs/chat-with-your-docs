"""Write the API's OpenAPI schema to frontend/openapi.json (the frontend's typed contract).

Run from backend/: `uv run python -m scripts.export_openapi`. Builds the schema from the app
object without starting it: no settings, database or provider keys are needed. The output is
committed; `npm --prefix frontend run api:types` turns it into src/api/schema.d.ts.
"""

import json
from pathlib import Path

from app.main import create_app

OUTPUT = Path(__file__).resolve().parents[2] / "frontend" / "openapi.json"


def main() -> None:
    schema = create_app().openapi()
    OUTPUT.write_text(json.dumps(schema, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Wrote {OUTPUT}")


if __name__ == "__main__":
    main()
