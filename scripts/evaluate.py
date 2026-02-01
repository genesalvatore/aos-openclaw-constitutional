"""Evaluate a constitution against a proposed tool call.

This is the Phase 1 reference evaluator meant to be lifted into a Gateway hook.

It does NOT execute tools. It returns:
- decision: allow|confirm|deny
- reason_code
- obligations (merged)
- scope_hash (only for confirm)
- risk + classifications (for audit)

Usage:
  python scripts/evaluate.py --constitution constitution.yaml --tool message.send --args '{"message":"hi"}' --intent '{"user_requested":true,"explicit_confirmation":true}'

Notes:
- Rules are evaluated deterministically.
- Decision lattice: deny > confirm > allow
- Two-pass evaluation to support rules that match on `when.decision`.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

# Ensure sibling imports work when executed as a script.
sys.path.insert(0, os.path.dirname(__file__))

try:
    import yaml  # pyyaml
except ImportError as e:
    raise SystemExit("Missing dependency: pyyaml. Install with: pip install pyyaml") from e

from classify import classify as classify_tags


ORDER = {"allow": 0, "confirm": 1, "deny": 2}


def c14n_json(obj: Any) -> bytes:
    # Deterministic JSON encoding with sorted keys.
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode("utf-8")


def max_decision(a: str, b: str) -> str:
    return a if ORDER[a] >= ORDER[b] else b


def risk_ge(risk: str, at_least: str) -> bool:
    levels = ["low", "medium", "high", "critical"]
    return levels.index(risk) >= levels.index(at_least)


def tool_matches(tool: str, matcher: Any) -> bool:
    if matcher == "*":
        return True
    return tool == matcher


def path_prefix_any(path: Optional[str], prefixes: List[str], env: Dict[str, str]) -> bool:
    if not path or not isinstance(path, str):
        return False
    p = path
    # Simple ${WORKSPACE} substitution.
    for pref in prefixes:
        pref_s = str(pref)
        for k, v in env.items():
            pref_s = pref_s.replace("${" + k + "}", v)
        if p.lower().startswith(pref_s.lower()):
            return True
    return False


@dataclass
class EvalResult:
    decision: str = "allow"
    reason_code: Optional[str] = None
    obligations: Dict[str, Any] = field(default_factory=dict)
    scope_hash: Optional[str] = None
    matched_rules: List[str] = field(default_factory=list)


def merge_obligations(dst: Dict[str, Any], src: Dict[str, Any]) -> Dict[str, Any]:
    # Shallow merge with dict union; for nested dicts, merge recursively.
    for k, v in (src or {}).items():
        if k in dst and isinstance(dst[k], dict) and isinstance(v, dict):
            dst[k] = merge_obligations(dst[k], v)
        else:
            dst[k] = v
    return dst


def match_when(rule_when: Dict[str, Any], *, tool: str, risk: str, classifications: List[str], decision: str) -> bool:
    if not rule_when:
        return True

    if "tool" in rule_when and not tool_matches(tool, rule_when["tool"]):
        return False

    if "tool_any_of" in rule_when and tool not in [str(x) for x in rule_when["tool_any_of"]]:
        return False

    if "risk_at_least" in rule_when and not risk_ge(risk, str(rule_when["risk_at_least"])):
        return False

    if "classification_any_of" in rule_when:
        wanted = set(str(x) for x in rule_when["classification_any_of"])
        if not wanted.intersection(classifications):
            return False

    if "decision" in rule_when and str(rule_when["decision"]) != decision:
        return False

    return True


def evaluate_rules(constitution: Dict[str, Any], *, tool: str, args: Dict[str, Any], risk: str, classifications: List[str], decision: str, env: Dict[str, str]) -> Tuple[str, Dict[str, Any], List[str], Optional[str]]:
    out_decision = decision
    obligations: Dict[str, Any] = {}
    matched: List[str] = []
    reason_code: Optional[str] = None

    rules = constitution.get("rules") or []

    for rule in rules:
        rid = str(rule.get("id") or "")
        when = rule.get("when") or {}

        if not match_when(when, tool=tool, risk=risk, classifications=classifications, decision=out_decision):
            continue

        matched.append(rid)

        # allow_if / otherwise gating (minimal support)
        if "allow_if" in rule:
            allow_if = rule.get("allow_if") or {}
            # path-based allowlist for read/write/edit
            p = args.get("path") or args.get("file_path")
            if "path_prefix_any" in allow_if:
                ok = path_prefix_any(p if isinstance(p, str) else None, list(allow_if["path_prefix_any"]), env)
                if not ok:
                    otherwise = rule.get("otherwise") or {}
                    act = str(otherwise.get("action") or "confirm")
                    out_decision = max_decision(out_decision, act)
                    if act == "deny" and reason_code is None:
                        reason_code = rid
                    if act == "confirm" and reason_code is None and ORDER[out_decision] == ORDER["confirm"]:
                        reason_code = rid
                    continue

        # obligations
        if "require" in rule and isinstance(rule["require"], dict):
            merge_obligations(obligations, rule["require"])

        # allow_override
        if "allow_override" in rule and isinstance(rule["allow_override"], dict):
            merge_obligations(obligations, {"allow_override": rule["allow_override"]})

        # decision
        act = str(rule.get("action") or "allow")
        out_decision = max_decision(out_decision, act)

        if reason_code is None and act in ("deny", "confirm"):
            reason_code = rid

    return out_decision, obligations, matched, reason_code


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--constitution", required=True)
    ap.add_argument("--tool", required=True)
    ap.add_argument("--args", default=None, help="JSON object")
    ap.add_argument("--args-file", default=None, help="Path to a JSON file containing args")
    ap.add_argument("--intent", default=None, help="JSON object")
    ap.add_argument("--intent-file", default=None, help="Path to a JSON file containing intent")
    ap.add_argument("--session-kind", default="main")
    ap.add_argument("--workspace", default=None, help="Workspace path for ${WORKSPACE} expansion")
    ap.add_argument("--policy-engine-version", default="phase1-ref-eval-1")
    ns = ap.parse_args()

    constitution = yaml.safe_load(open(ns.constitution, "r", encoding="utf-8").read())
    tool = ns.tool

    if not ns.args and not ns.args_file:
        raise SystemExit("Missing --args or --args-file")

    if ns.args_file:
        args = json.loads(open(ns.args_file, "r", encoding="utf-8").read())
    else:
        args = json.loads(ns.args)

    if ns.intent_file:
        intent = json.loads(open(ns.intent_file, "r", encoding="utf-8").read())
    else:
        intent = json.loads(ns.intent) if ns.intent else None

    env = {}
    if ns.workspace:
        env["WORKSPACE"] = ns.workspace

    # Compute risk + tags
    classified = classify_tags(tool, args, constitution=constitution, session_kind=ns.session_kind, intent=intent)
    risk = classified.risk.name
    classifications = sorted(classified.tags)

    # Start from defaults
    defaults = constitution.get("defaults") or {}
    base_policy = str(defaults.get("tool_policy") or "confirm")
    decision = base_policy

    # Pass 1: evaluate rules ignoring decision-matcher rules (we still run them, but they won't match unless decision already matches).
    decision1, obligations1, matched1, reason1 = evaluate_rules(constitution, tool=tool, args=args, risk=risk, classifications=classifications, decision=decision, env=env)

    # Pass 2: re-evaluate now that decision is known (enables when.decision rules like human override).
    decision2, obligations2, matched2, reason2 = evaluate_rules(constitution, tool=tool, args=args, risk=risk, classifications=classifications, decision=decision1, env=env)

    final_decision = max_decision(decision1, decision2)
    obligations = {}
    merge_obligations(obligations, obligations1)
    merge_obligations(obligations, obligations2)

    reason_code = reason1 or reason2

    # Scope hash for CONFIRM
    scope_hash = None
    if final_decision == "confirm":
        payload = {
            "tool": tool,
            "args": args,
            "constitution_doc_hash": constitution.get("doc_hash"),
            "policy_engine_version": ns.policy_engine_version,
        }
        scope_hash = "sha256:" + hashlib.sha256(c14n_json(payload)).hexdigest()

    out = {
        "decision": final_decision,
        "reason_code": reason_code,
        "risk": risk,
        "classifications": classifications,
        "obligations": obligations,
        "scope_hash": scope_hash,
        "matched_rules": sorted(set(matched1 + matched2)),
    }

    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
