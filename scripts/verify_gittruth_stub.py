"""Stub GitTruth verification.

This is an interface placeholder so teams can wire in their GitTruth client.

Expected contract: see `references/gittruth-attestation.contract.md`.

Gateway startup verification SHOULD do:
- verify Ed25519 (constitution.sig.json)
- verify GitTruth attestation for the commit containing constitution.yaml + constitution.sig.json

This stub only validates presence/shape of fields.

Usage:
  python scripts/verify_gittruth_stub.py constitution.attestation.json

Exit codes:
- 0: attestation contract looks structurally valid
- 1: invalid
"""

import json
import sys

REQUIRED = ["spec", "repo", "commit", "attestation_id", "tree_hash", "timestamp", "signature"]


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: python scripts/verify_gittruth_stub.py <constitution.attestation.json>", file=sys.stderr)
        return 2

    path = sys.argv[1]
    obj = json.loads(open(path, "r", encoding="utf-8").read())

    missing = [k for k in REQUIRED if k not in obj]
    if missing:
        print(f"Missing fields: {missing}", file=sys.stderr)
        return 1

    if obj.get("spec") != "gittruth-attestation-v1":
        print("Unsupported spec", file=sys.stderr)
        return 1

    if not str(obj["tree_hash"]).startswith("sha256:"):
        print("tree_hash must be sha256:<hex>", file=sys.stderr)
        return 1

    print("OK: attestation contract structurally valid (stub)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
