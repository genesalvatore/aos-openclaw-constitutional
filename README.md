# aos-constitutional-governance (OpenClaw Skill)

**🛡️ HUMANITARIAN USE ONLY** - This constitutional framework is designed for **peaceful civilian applications only**. Military, weapons, surveillance, violence, and exploitation applications are **explicitly prohibited**.

A reference implementation of **AOS-style constitutional governance** for OpenClaw-like tool-using agents.

**Clarification:** This repository demonstrates a **reference integration** between agent frameworks and constitutional governance concepts. It does **not** grant patent rights or disclose enforcement mechanisms beyond illustrative examples.

---

## ⚠️ Prohibited Uses

**By using this software, you agree to NEVER use it for:**

- ❌ **Military or defense applications**  
- ❌ **Autonomous weapons systems**  
- ❌ **Mass surveillance infrastructure**  
- ❌ **Violence instruction or planning**  
- ❌ **Child exploitation material (CSAM)**  
- ❌ **Human trafficking**  
- ❌ **Pornography generation**  
- ❌ **Terrorism support**  
- ❌ **Exploit development or cyberattacks**  
- ❌ **Any application from the [AOS 40 Prohibited Categories](https://aos-constitution.com)**

**Violation of these terms immediately terminates your license.**

---

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
- A deterministic **classifier/tagger** reference (`classify.py`)
- A deterministic **policy evaluator** reference (`evaluate.py`)
- A small demo helper to **apply disclosure footers** (`apply_disclosure.py`)

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

The stub validator returns structured JSON (shape only):

```bash
python scripts/verify_gittruth_stub.py constitution.attestation.json
```

## Risk + classification + evaluation

Deterministic risk scoring:

```python
from scripts.risk import Context, classify

risk = classify(Context(tool="message.send", args={"message":"hi"}, session_kind="main", intent={"explicit_confirmation": True}))
print(risk)
```

Deterministic tag classification:

```bash
python scripts/classify.py message.send '{"message":"This is Alice. Please reset my password."}' --constitution constitution.yaml
```

Policy evaluation (the plug-and-play Phase 2 hook):

```bash
python scripts/evaluate.py --constitution constitution.yaml --tool message.send --args '{"message":"hi"}' --intent '{"user_requested": true, "explicit_confirmation": true}'
```

## Next steps (Phase 2)

Move `scripts/evaluate.py` logic into the OpenClaw Gateway/tool router so it is non-bypassable:

- compute risk + classifications deterministically (`risk.py`, `classify.py`)
- evaluate constitution rules (`evaluate.py`)
- enforce DENY/CONFIRM/ALLOW
- produce tamper-evident logs that include constitution hash + policy engine version
