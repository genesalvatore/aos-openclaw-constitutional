"""Sign constitution.yaml using Ed25519 over sha256(canonical_json_bytes).

Produces a detached signature JSON compatible with GitTruth commit attestation flows.

Usage:
  python scripts/sign.py constitution.yaml --sk <base64_or_hex_secret_key> --out constitution.sig.json

Notes:
- This script signs the *doc_hash* (sha256 of canonical JSON bytes).
- You can store the secret key in an env var and pass it in.
"""

import argparse
import base64
import hashlib
import json
import os
import sys

try:
    from nacl.signing import SigningKey
except ImportError as e:
    raise SystemExit("Missing dependency: pynacl. Install with: pip install pynacl") from e

from pathlib import Path


def _decode_key(s: str) -> bytes:
    s = s.strip()
    # accept hex (64 chars) or base64
    try:
        if all(c in "0123456789abcdefABCDEF" for c in s) and len(s) in (64, 128):
            return bytes.fromhex(s)
        return base64.b64decode(s)
    except Exception as e:
        raise SystemExit(f"Could not decode secret key: {e}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("yaml_path")
    ap.add_argument("--sk", default=os.environ.get("AOS_ED25519_SK"), help="Ed25519 secret key (hex/base64) or env AOS_ED25519_SK")
    ap.add_argument("--key-id", default=os.environ.get("AOS_KEY_ID", "ed25519:UNSPECIFIED"))
    ap.add_argument("--out", required=True)
    ap.add_argument("--signed-at", default=None)
    args = ap.parse_args()

    if not args.sk:
        print("Missing --sk (or env AOS_ED25519_SK)", file=sys.stderr)
        return 2

    yaml_path = Path(args.yaml_path)
    # canonicalize by shelling to c14n.py would be brittle; implement minimal inline
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

    data = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
    c14n = json.dumps(sort_keys(data), ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    doc_hash_bytes = hashlib.sha256(c14n).digest()
    doc_hash = "sha256:" + hashlib.sha256(c14n).hexdigest()

    sk_bytes = _decode_key(args.sk)
    signing_key = SigningKey(sk_bytes)
    sig = signing_key.sign(doc_hash_bytes).signature

    payload = {
        "spec": "aos-policy-signature-v1",
        "doc_hash": doc_hash,
        "signed_at": args.signed_at,
        "key_id": args.key_id,
        "signature": base64.b64encode(sig).decode("ascii"),
    }

    Path(args.out).write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(doc_hash)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
