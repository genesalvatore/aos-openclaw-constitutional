"""Canonicalize constitution.yaml to canonical JSON for hashing/signing.

Usage:
  python scripts/c14n.py path/to/constitution.yaml > constitution.c14n.json

Rules:
- YAML parse
- Recursively sort dict keys
- Emit compact JSON (UTF-8)
"""

import json
import sys
from typing import Any

try:
    import yaml  # pyyaml
except ImportError as e:
    raise SystemExit("Missing dependency: pyyaml. Install with: pip install pyyaml") from e


def sort_keys(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {k: sort_keys(obj[k]) for k in sorted(obj.keys())}
    if isinstance(obj, list):
        return [sort_keys(x) for x in obj]
    return obj


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: python scripts/c14n.py <constitution.yaml>", file=sys.stderr)
        return 2

    path = sys.argv[1]
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    data = sort_keys(data)
    # separators remove whitespace for stable bytes
    sys.stdout.write(json.dumps(data, ensure_ascii=False, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
