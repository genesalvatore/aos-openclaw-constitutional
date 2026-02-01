"""Deterministic classification tags for OpenClaw-style tool calls.

Goal: produce reproducible tags (no LLM judgment) for constitutional rules.

This is a reference implementation. Expand the matchers as needed.

Usage:
  python scripts/classify.py <tool> <args_json> [--constitution constitution.yaml]
  python scripts/classify.py <tool> --args-file args.json [--constitution constitution.yaml]

Output:
  JSON: {"risk": "high", "classifications": [..], "details": {...}}
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set

# Ensure sibling imports work when executed as a script.
sys.path.insert(0, os.path.dirname(__file__))

try:
    import yaml  # pyyaml
except ImportError as e:
    raise SystemExit("Missing dependency: pyyaml. Install with: pip install pyyaml") from e

from risk import Context as RiskContext, Risk, classify as classify_risk


@dataclass
class Classified:
    risk: Risk
    tags: Set[str]
    details: Dict[str, Any]


def _get_allowlist_domains(constitution: Optional[Dict[str, Any]]) -> List[str]:
    if not constitution:
        return []
    egress = constitution.get("egress") or {}
    domains = egress.get("allowlist_domains") or []
    return [str(d).lower() for d in domains]


def _extract_domains_from_args(tool: str, args: Dict[str, Any]) -> List[str]:
    # Best-effort extraction for common tool shapes.
    domains: List[str] = []

    def add_from_url(url: str):
        m = re.match(r"^https?://([^/]+)", url.strip(), re.I)
        if m:
            domains.append(m.group(1).lower())

    if tool == "web_fetch":
        url = args.get("url")
        if isinstance(url, str):
            add_from_url(url)

    if tool.startswith("browser."):
        url = args.get("targetUrl") or args.get("url")
        if isinstance(url, str):
            add_from_url(url)

    if tool in ("message.send", "message.broadcast"):
        # messaging doesn't expose a domain; treat as egress but not domain-scoped.
        pass

    return domains


IMPERSONATION_PATTERNS = [
    re.compile(r"\bthis is\s+([A-Z][a-z]+)\b"),
    re.compile(r"\bi am\s+([A-Z][a-z]+)\b"),
    re.compile(r"\bfrom\s+([A-Z][a-z]+)\b"),
]

AI_DISCLOSURE_HINT = re.compile(r"\b(ai|assistant|bot)\b", re.I)


def classify(tool: str, args: Dict[str, Any], *, constitution: Optional[Dict[str, Any]] = None, session_kind: str = "main", intent: Optional[Dict[str, Any]] = None) -> Classified:
    tags: Set[str] = set()
    details: Dict[str, Any] = {}

    risk = classify_risk(RiskContext(tool=tool, args=args, session_kind=session_kind, intent=intent))

    # Hidden action: if this tool call wasn't explicitly requested/approved.
    # Convention: intent.user_requested == True means user directly asked for it.
    if intent is not None and intent.get("user_requested") is False:
        tags.add("hidden_action")

    # Path privacy
    if tool in ("read", "write", "edit"):
        p = args.get("path") or args.get("file_path")
        if isinstance(p, str):
            details["path"] = p
            # If caller provides a workspace prefix in intent, we can flag unauthorized reads.
            workspace = (intent or {}).get("workspace")
            if isinstance(workspace, str) and not p.lower().startswith(workspace.lower()):
                tags.add("unauthorized_file_access")

    # Egress allowlist (domain-scoped tools)
    allowlist = _get_allowlist_domains(constitution)
    domains = _extract_domains_from_args(tool, args)
    if domains:
        details["domains"] = domains
        if allowlist:
            details["allowlist_domains"] = allowlist
            for d in domains:
                if d not in allowlist and not any(d.endswith("." + a) for a in allowlist):
                    tags.add("unauthorized_egress")

    # Messaging deception/impersonation heuristics
    if tool in ("message.send", "message.broadcast"):
        msg = str(args.get("message") or "")
        if msg:
            details["message_len"] = len(msg)
            # If message claims identity without AI disclosure, flag impersonation.
            claims = any(p.search(msg) for p in IMPERSONATION_PATTERNS)
            has_disclosure = bool(AI_DISCLOSURE_HINT.search(msg))
            if claims and not has_disclosure:
                tags.add("impersonation")

            # Simple reputational-harm heuristic (expand as needed)
            if re.search(r"\b(defame|ruin|expose|leak|doxx)\b", msg, re.I):
                tags.add("harm_reputational")

    # Exec harm heuristics
    if tool == "exec":
        cmd = " ".join(args.get("command", [])) if isinstance(args.get("command"), list) else str(args.get("command", ""))
        details["command"] = cmd
        if re.search(r"\b(rm\s+-rf|del\s+/s|format\b)\b", cmd, re.I):
            tags.add("harm_financial")

    # Promote certain tags to constitutional prohibition
    if tags.intersection({"impersonation", "harm_financial", "harm_physical", "harm_reputational"}):
        tags.add("constitutionally_prohibited")

    return Classified(risk=risk, tags=tags, details=details)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("tool")
    ap.add_argument("args_json", nargs="?")
    ap.add_argument("--args-file", default=None)
    ap.add_argument("--constitution", default=None)
    ap.add_argument("--session-kind", default="main")
    ap.add_argument("--intent", default=None, help="JSON string")
    ns = ap.parse_args()

    if ns.args_file:
        args = json.loads(open(ns.args_file, "r", encoding="utf-8").read())
    elif ns.args_json:
        args = json.loads(ns.args_json)
    else:
        print("Missing args: provide <args_json> or --args-file", file=sys.stderr)
        return 2
    constitution = None
    if ns.constitution:
        constitution = yaml.safe_load(open(ns.constitution, "r", encoding="utf-8").read())
    intent = json.loads(ns.intent) if ns.intent else None

    out = classify(ns.tool, args, constitution=constitution, session_kind=ns.session_kind, intent=intent)
    print(json.dumps({
        "risk": out.risk.name,
        "classifications": sorted(out.tags),
        "details": out.details,
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
