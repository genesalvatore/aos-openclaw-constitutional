# GitTruth Attestation Contract (minimal)

This Skill assumes a GitTruth system that produces an immutable attestation for a git commit.

## File: `constitution.attestation.json`

Minimal JSON contract (v1):

```json
{
  "spec": "gittruth-attestation-v1",
  "repo": "https://github.com/<org>/<repo>",
  "commit": "<40-hex sha1 or other commit id>",
  "attestation_id": "<gittruth id>",
  "tree_hash": "sha256:<hex>",
  "timestamp": "2026-02-01T00:00:00Z",
  "signature": "<base64 signature over the fields above>"
}
```

## Semantics

- `repo` + `commit` identify the git object being attested.
- `tree_hash` is the hash of the repository tree at `commit`.
  - Recommended: compute `tree_hash = sha256(<canonical tree listing + blob hashes>)`.
  - The canonical tree listing must be deterministic and specified by GitTruth.
- `signature` is GitTruth's signature over a canonical encoding of the attestation payload (GitTruth-defined).

## Verification requirements (Gateway startup)

The Gateway must:

1. Verify the constitution Ed25519 signature (see `scripts/verify.py`).
2. Verify the GitTruth attestation:
   - attestation is valid under GitTruth trust roots
   - `repo` and `commit` match the local checkout
   - `tree_hash` matches the computed tree hash for that commit
   - the attested commit tree contains the exact bytes (or blob hashes) for:
     - `constitution.yaml`
     - `constitution.sig.json`
     - (optional) `constitution.c14n.json` (can be derived)

This contract is intentionally minimal; your GitTruth client can carry richer fields.
