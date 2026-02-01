"""Stub GitTruth verification.

This file defines the **interface** expected from a GitTruth verifier.

Expected contract input: see `references/gittruth-attestation.contract.md`.

Expected verifier output (structured JSON):

```json
{
  "ok": true,
  "verified_tree_hash": "sha256:<hex>",
  "verified_commit": "<commit>",
  "trust_root": "<trust-root-id>",
  "attestation_id": "<gittruth id>",
  "timestamp": "<rfc3339>"
}
```

This stub only validates presence/shape of fields and echoes them back as a
successful verification result. Replace with a real GitTruth client.

Usage:
  python scripts/verify_gittruth_stub.py constitution.attestation.json
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
        print(json.dumps({"ok": False, "error": f"Missing fields: {missing}"}))
        return 1

    if obj.get("spec") != "gittruth-attestation-v1":
        print(json.dumps({"ok": False, "error": "Unsupported spec"}))
        return 1

    if not str(obj["tree_hash"]).startswith("sha256:"):
        print(json.dumps({"ok": False, "error": "tree_hash must be sha256:<hex>"}))
        return 1

    # Stubbed success response (real implementation must verify signature + tree_hash).
    out = {
        "ok": True,
        "verified_tree_hash": obj["tree_hash"],
        "verified_commit": obj["commit"],
        "trust_root": "STUB-TRUST-ROOT",
        "attestation_id": obj["attestation_id"],
        "timestamp": obj["timestamp"],
    }
    print(json.dumps(out, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
