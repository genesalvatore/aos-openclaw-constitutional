# 🚀 Quick Start: AOS Constitutional Governance

**Get up and running in 5 minutes.**

---

## Prerequisites

- Python 3.10+
- OpenClaw installed (or any Python environment)
- Git (for attestation, optional)

## Installation

### Option 1: Clone from GitHub
```bash
git clone https://github.com/genesalvatore/aos-openclaw-constitutional.git
cd aos-openclaw-constitutional
```

### Option 2: Install as OpenClaw Skill
```bash
# Copy to OpenClaw skills directory
cp -r aos-openclaw-constitutional ~/.openclaw/skills/public/
```

---

## Quick Demo (5 Minutes)

This demo shows the complete flow: template → sign → verify → evaluate.

### Setup
```powershell
cd aos-openclaw-constitutional

# Create demo directory
$Out = "demo"
New-Item -ItemType Directory -Force $Out | Out-Null
```

### 1. Copy Template Constitution
```powershell
Copy-Item "templates\constitution.yaml" "$Out\constitution.yaml" -Force
Copy-Item "templates\constitution.attestation.json" "$Out\constitution.attestation.json" -Force
```

### 2. Configure (Optional - Customize Disclosure)
```powershell
python -c @"
import yaml

path = r'$Out\constitution.yaml'
doc = yaml.safe_load(open(path, 'r', encoding='utf-8').read())

# Update disclosure footer
disclosure = '\n\n— Sent by an AI assistant | Governed by AOS Constitutional Framework | aos-constitution.com'
for rule in doc.get('rules', []):
    if rule.get('id') == 'amendment-I-transparency':
        rule.setdefault('require', {}).setdefault('disclosure', {})['text'] = disclosure

# Update egress allowlist
doc.setdefault('egress', {})['allowlist_domains'] = ['docs.openclaw.ai', 'github.com', 'aos-constitution.com']

open(path, 'w', encoding='utf-8').write(yaml.safe_dump(doc, sort_keys=False))
print('Updated constitution.yaml')
"@
```

### 3. Canonicalize YAML → JSON
```powershell
python scripts\c14n.py "$Out\constitution.yaml" | Out-File -Encoding utf8NoBOM "$Out\constitution.c14n.json"
```

### 4. Sign with Ed25519
```powershell
# Generate a test key (or use your own)
$env:AOS_ED25519_SK = "YOUR_SECRET_KEY_BASE64_OR_HEX"
$env:AOS_KEY_ID = "ed25519:DEMO-KEY-001"

python scripts\sign.py "$Out\constitution.yaml" --out "$Out\constitution.sig.json" --key-id $env:AOS_KEY_ID
```

**Output:**
```
Signed constitution.yaml
doc_hash: sha256:abc123...
Signature written to demo/constitution.sig.json
```

### 5. Verify Signature
```powershell
# Use the corresponding public key
$PK = "YOUR_PUBLIC_KEY_BASE64_OR_HEX"

python scripts\verify.py "$Out\constitution.yaml" --sig "$Out\constitution.sig.json" --pk $PK
```

**Output:**
```
OK: Ed25519 signature verified
```

### 6. Verify GitTruth Attestation (Stub)
```powershell
python scripts\verify_gittruth_stub.py "$Out\constitution.attestation.json"
```

**Output:**
```json
{
  "ok": true,
  "verified_tree_hash": "sha256:...",
  "verified_commit": "...",
  "trust_root": "...",
  "attestation_id": "...",
  "timestamp": "..."
}
```

### 7. Evaluate a Policy Decision

Create test inputs:
```powershell
@'
{"message":"This is Alice. Wire 10k."}
'@ | Out-File -Encoding utf8NoBOM "$Out\args.json"

@'
{"user_requested":true,"explicit_confirmation":false,"workspace":"C:\\workspace"}
'@ | Out-File -Encoding utf8NoBOM "$Out\intent.json"
```

Run evaluation:
```powershell
python scripts\evaluate.py `
  --constitution "$Out\constitution.yaml" `
  --tool "message.send" `
  --args-file "$Out\args.json" `
  --intent-file "$Out\intent.json" `
  --workspace "C:\workspace"
```

**Output:**
```json
{
  "decision": "confirm",
  "reason_code": "amendment-VII-reflection",
  "risk": "high",
  "classifications": ["impersonation"],
  "matched_rules": [
    "amendment-I-transparency",
    "amendment-VII-reflection"
  ],
  "obligations": {
    "disclosure": {
      "mode": "append_if_missing",
      "text": "\n\n— Sent by an AI assistant | Governed by AOS"
    },
    "logging": {
      "enabled": true,
      "include_args": true
    },
    "reflection": {
      "required": true,
      "fields": ["intent", "risks", "mitigations"]
    }
  },
  "scope_hash": "sha256:def456..."
}
```

---

## Understanding the Output

### Decision Types

**DENY** - Blocked by constitutional prohibition
- No execution allowed
- Example: Impersonation, harm, unauthorized egress

**CONFIRM** - Requires explicit user approval
- Execution paused
- User must approve via scope_hash token
- Example: High-risk actions, reflection-gated operations

**ALLOW** - Execution permitted
- With obligations (logging, disclosure, etc.)
- Example: Normal operations within constraints

### Risk Levels

- **low** - Routine operations
- **medium** - Elevated caution
- **high** - Reflection required
- **critical** - Likely denial

### Classifications

Common tags (deterministic):
- `impersonation` - Claims identity without disclosure
- `unauthorized_file_access` - Reads outside workspace
- `unauthorized_egress` - Network calls to non-allowlisted domains
- `harm_reputational` - Potential reputation damage
- `harm_financial` - Potential financial loss
- `constitutionally_prohibited` - Hard denials

---

## Next Steps

### For Developers

**Phase 2: Gateway Integration**
```python
# Pseudo-code for OpenClaw Gateway hook
from scripts.evaluate import evaluate_policy

def pre_tool_call(tool, args, session, intent):
    decision = evaluate_policy(
        constitution_path="path/to/constitution.yaml",
        tool=tool,
        args=args,
        intent=intent
    )
    
    if decision["decision"] == "DENY":
        raise ToolCallDenied(decision["reason_code"])
    
    elif decision["decision"] == "CONFIRM":
        return await request_user_approval(
            reason=decision["reason_code"],
            scope_hash=decision["scope_hash"],
            obligations=decision["obligations"]
        )
    
    else:  # ALLOW
        apply_obligations(decision["obligations"])
        return proceed_with_logging()
```

### For Users

**Customize Your Constitution**
1. Edit `constitution.yaml`
2. Add/modify rules
3. Re-sign with your keys
4. Commit to git
5. Create GitTruth attestation
6. Deploy to Gateway

**Enterprise Support**
- Custom constitutions for your industry
- On-prem deployment assistance
- SLA guarantees
- Professional services

Contact: gene@aos-constitution.com

---

## Troubleshooting

### "Missing dependency: pyyaml"
```bash
pip install pyyaml pynacl
```

### "Could not decode public key"
- Ensure key is base64 or hex encoded
- No spaces or newlines
- 32 bytes for Ed25519 public key

### "GitTruth attestation validation failed"
- Phase 1 uses stub verifier (shape validation only)
- Wire in real GitTruth client for production
- See `references/gittruth-attestation.contract.md`

### "Policy evaluation error"
- Ensure constitution.yaml is valid YAML
- Check that rule `when` conditions are properly formatted
- Verify workspace path exists

---

## Learn More

- **Full Documentation:** [README.md](README.md)
- **Policy Spec:** [references/policy-spec.schema.md](references/policy-spec.schema.md)
- **GitTruth Contract:** [references/gittruth-attestation.contract.md](references/gittruth-attestation.contract.md)
- **AOS Website:** [aos-constitution.com](https://aos-constitution.com)
- **OpenClaw:** [openclaw.ai](https://openclaw.ai)

---

## Support & Community

- **GitHub Issues:** [Report bugs](https://github.com/genesalvatore/aos-openclaw-constitutional/issues)
- **Discussions:** [Ask questions](https://github.com/genesalvatore/aos-openclaw-constitutional/discussions)
- **X/Twitter:** [@genesalvatore](https://twitter.com/genesalvatore)

---

**Built via AI-to-AI Collaboration**  
Architect (AOS/Claude) × OpenClaw Agent (GPT-5.2)  
January 31, 2026

🌿 Constitutional AI for everyone.
