"""Deterministic risk classification for OpenClaw-style tool calls.

This is a reference implementation for a Gateway policy engine.

Risk levels: low < medium < high < critical

Computation:
  risk = max(
    tool_base_risk(tool),
    arg_risk(tool,args),
    data_risk(args),
    egress_risk(tool,args),
    scope_risk(session,intent)
  )

The design goal is **predictability** and **auditability**, not cleverness.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum
from typing import Any, Dict, Optional


class Risk(IntEnum):
    low = 0
    medium = 1
    high = 2
    critical = 3


TOOL_BASE: Dict[str, Risk] = {
    # messaging / external effect
    "message.send": Risk.high,
    "message.broadcast": Risk.critical,

    # filesystem
    "read": Risk.medium,
    "write": Risk.high,
    "edit": Risk.high,

    # execution
    "exec": Risk.critical,

    # web
    "web_fetch": Risk.medium,
    "browser.navigate": Risk.medium,
    "browser.upload": Risk.high,

    # sensors / nodes
    "nodes.location_get": Risk.high,
    "nodes.camera_snap": Risk.high,
    "nodes.screen_record": Risk.high,
}


SENSITIVE_PATH_HINTS = [
    "\\AppData\\", "\\.ssh\\", "id_rsa", "id_ed25519", "password", "secrets", "token",
]


@dataclass
class Context:
    tool: str
    args: Dict[str, Any]
    session_kind: str = "main"
    intent: Optional[Dict[str, Any]] = None


def tool_base_risk(tool: str) -> Risk:
    return TOOL_BASE.get(tool, Risk.medium)


def arg_risk(tool: str, args: Dict[str, Any]) -> Risk:
    # crude but deterministic heuristics
    if tool == "exec":
        cmd = " ".join(args.get("command", [])) if isinstance(args.get("command"), list) else str(args.get("command", ""))
        # network + deletion patterns
        if any(x in cmd.lower() for x in ["curl ", "wget ", "Invoke-WebRequest".lower(), "scp ", "ssh "]):
            return Risk.critical
        if any(x in cmd.lower() for x in ["rm ", "rmdir", "del ", "format", ":(){"]):
            return Risk.critical
        return Risk.high

    if tool in ("read", "write", "edit"):
        p = args.get("path") or args.get("file_path")
        if isinstance(p, str) and any(h.lower() in p.lower() for h in SENSITIVE_PATH_HINTS):
            return Risk.high
        return Risk.medium

    if tool in ("message.send", "message.broadcast"):
        msg = (args.get("message") or "")
        if len(msg) > 2000:
            return Risk.high
        return Risk.high

    return Risk.low


def egress_risk(tool: str, args: Dict[str, Any]) -> Risk:
    # treat anything that can send data outward as higher risk
    if tool in ("message.send", "message.broadcast", "browser.upload"):
        return Risk.high
    if tool == "web_fetch":
        return Risk.medium
    return Risk.low


def scope_risk(session_kind: str, intent: Optional[Dict[str, Any]]) -> Risk:
    # If there's no explicit user intent object, raise risk for impactful tools
    if not intent:
        return Risk.medium
    if intent.get("explicit_confirmation") is True:
        return Risk.low
    return Risk.medium


def classify(ctx: Context) -> Risk:
    return max(
        tool_base_risk(ctx.tool),
        arg_risk(ctx.tool, ctx.args),
        egress_risk(ctx.tool, ctx.args),
        scope_risk(ctx.session_kind, ctx.intent),
    )
