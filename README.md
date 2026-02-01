# aos-constitutional-governance (OpenClaw Skill)

A reference implementation of **AOS-style constitutional governance** for OpenClaw-like tool-using agents.

## What this is

This Skill provides:

- A **minimal constitution policy spec** (`constitution.yaml`) that is:
  - human-readable (YAML)
  - deterministically signable (canonical JSON)
- Tooling to:
  - canonicalize (`c14n.py`)
  - sign with **Ed25519** (`sign.py`)
  - verify Ed25519 signatures (`verify.py`)
  - validate a **GitTruth attestation contract** (stub) (`verify_gittruth_stub.py`)
- A deterministic **risk classifier** reference (`risk.py`)

This is **Phase 1**: artifacts + spec + verification + reference algorithms.

**Important:** Real immutability requires **Gateway/tool-router enforcement** (Phase 2). A Skill alone cannot prevent an agent from attempting prohibited tool calls.

## Files

- `templates/constitution.yaml` — reference constitution with the 10 AOS bedrock amendments
- `templates/constitution.attestation.json` — minimal GitTruth attestation contract example

## Signing flow (recommended)

1. Copy template:
   - `templates/constitution.yaml` → `constitution.yaml`
2. Canonicalize:

```bash
python scripts/c14n.py constitution.yaml > constitution.c14n.json
```

3. Sign (Ed25519) over `sha256(canonical_json_bytes)`:

```bash
# Provide secret key via env var (base64 or hex)
set AOS_ED25519_SK=... 
python scripts/sign.py constitution.yaml --out constitution.sig.json --key-id ed25519:ARCHITECT-ROOT-001
```

The script prints the computed `doc_hash` (sha256).

4. Commit to git:
   - `constitution.yaml`
   - `constitution.sig.json`

5. Run GitTruth attestation for that commit.

6. On Gateway startup:
   - verify Ed25519 signature (`scripts/verify.py`)
   - verify GitTruth attestation (wire in your GitTruth client)

## GitTruth attestation contract

See:
- `references/gittruth-attestation.contract.md`

The stub validator checks shape only:

```bash
python scripts/verify_gittruth_stub.py constitution.attestation.json
```

## Risk classification

For deterministic risk scoring:

```python
from scripts.risk import Context, classify

risk = classify(Context(tool="message.send", args={"message":"hi"}, session_kind="main", intent={"explicit_confirmation": True}))
print(risk)
```

## Next steps (Phase 2)

Implement the policy evaluator inside the OpenClaw Gateway/tool router:

- compute risk + classifications deterministically
- evaluate constitution rules
- enforce DENY/CONFIRM/ALLOW
- produce tamper-evident logs that include constitution hash + policy engine version
