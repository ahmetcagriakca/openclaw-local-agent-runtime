"""Export OpenAPI spec from FastAPI app — D-100.

Usage: python tools/export_openapi.py
Output: docs/api/openapi.json
"""
import json
import os
import sys
from pathlib import Path

# Add agent/ to path so imports work
SCRIPT_DIR = Path(__file__).resolve().parent
OC_ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(OC_ROOT / "agent"))

# Minimal env setup to avoid startup side effects
os.environ.setdefault("MCC_PORT", "8003")

from api.server import app  # noqa: E402

spec = app.openapi()

output_path = OC_ROOT / "docs" / "api" / "openapi.json"
output_path.parent.mkdir(parents=True, exist_ok=True)
output_path.write_text(json.dumps(spec, indent=2, ensure_ascii=False), encoding="utf-8")

endpoint_count = sum(
    len(methods) for methods in spec.get("paths", {}).values()
)
print(f"OpenAPI spec exported to {output_path}")
print(f"  Endpoints: {endpoint_count}")
print(f"  Schemas: {len(spec.get('components', {}).get('schemas', {}))}")
print(f"  Paths: {len(spec.get('paths', {}))}")
