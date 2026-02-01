# AOS/OpenClaw Minimal Constitution Policy Spec (v1)

This is a **reference** schema and semantics doc for `constitution.yaml`.

## Canonicalization

- Source file: YAML
- Canonical form: JSON
- Canonicalization rules:
  - Parse YAML to native objects
  - Convert to JSON with:
    - UTF-8 encoding
    - No insignificant whitespace
    - Object keys sorted lexicographically at all levels
    - Arrays preserve order
  - Hash = `sha256(canonical_json_bytes)`

## Decision lattice

Most restrictive wins:

`DENY > CONFIRM > ALLOW`

Obligations merge (union) across all matched rules.

## Minimal fields

Top-level:
- `version` (int)
- `id` (string)
- `revision` (string)
- `doc_hash` (string, `sha256:<hex>`)
- `immutability.locked` (bool)
- `immutability.gittruth` (object; pointers)
- `defaults` (object)
- `rules[]` (array)

Rule object:
- `id` (string)
- `when` matcher (tool/risk/classification/decision)
- `action` OR `require` / `allow_if` / `otherwise`
- `reason` or `reason_code`

Matchers (minimal):
- `tool`: exact match or `*`
- `tool_any_of`: list
- `risk_at_least`: low|medium|high|critical
- `classification_any_of`: list

Conditions (minimal):
- `allow_if.path_prefix_any`: list of prefixes
- `require.disclosure`: {mode, text}
- `require.logging`: {enabled, include_args, include_result, tamper_evident}
- `require.reflection`: {required, fields[]}

Outcomes:
- `action`: allow|confirm|deny

Override (confirm only):
- `allow_override`: {mode: one_time, scope: exact_call, audit: true}

## Risk computation (reference)

The runtime computes risk deterministically from tool+args.
See `scripts/risk.py` for a rules-based scorer.
