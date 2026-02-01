"""Verify constitution.yaml against Ed25519 signature + (optionally) GitTruth attestation.

Usage:
  python scripts/verify.py constitution.yaml --sig constitution.sig.json --pk <hex/base64_public_key>

GitTruth verification is left as a pluggable step (depends on your GitTruth client).
The verifier should:
- load attestation pointer (commit, attestation id)
- verify it matches repo+commit
- ensure commit contains the exact constitution.yaml + signature file bytes hashed

This script verifies Ed25519 over doc_hash bytes.
"""

import argparse
import base64
import hashlib
import json
import sys

try:
    from nacl.signing import VerifyKey
except ImportError as e:
    raise SystemExit("Missing dependency: pynacl. Install with: pip install pynacl") from e


def _decode_key(s: str) -> bytes:
    s = s.strip()
    try:
        if all(c in "0123456789abcdefABCDEF" for c in s) and len(s) in (64, 128):
            return bytes.fromhex(s)
        return base64.b64decode(s)
    except Exception as e:
        raise SystemExit(f"Could not decode public key: {e}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("yaml_path")
    ap.add_argument("--sig", required=True)
    ap.add_argument("--pk", required=True)
    args = ap.parse_args()

    try:
        import yaml
    except ImportError as e:
        raise SystemExit("Missing dependency: pyyaml. Install with: pip install pyyaml") from e

    def sort_keys(obj):
        if isinstance(obj, dict):
            return {k: sort_keys(obj[k]) for k in sorted(obj.keys())}
        if isinstance(obj, list):
            return [sort_keys(x) for x in obj]
        return obj

    with open(args.yaml_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    c14n = json.dumps(sort_keys(data), ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    doc_hash_bytes = hashlib.sha256(c14n).digest()
    doc_hash = "sha256:" + hashlib.sha256(c14n).hexdigest()

    sig_obj = json.loads(open(args.sig, "r", encoding="utf-8").read())
    if sig_obj.get("doc_hash") != doc_hash:
        print(f"doc_hash mismatch: expected {doc_hash}, got {sig_obj.get('doc_hash')}", file=sys.stderr)
        return 1

    sig = base64.b64decode(sig_obj["signature"])
    pk_bytes = _decode_key(args.pk)
    vk = VerifyKey(pk_bytes)
    try:
        vk.verify(doc_hash_bytes, sig)
    except Exception as e:
        print(f"signature invalid: {e}", file=sys.stderr)
        return 1

    print("OK: Ed25519 signature verified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
