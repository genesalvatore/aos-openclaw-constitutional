"""Apply disclosure obligation to an outbound message.

This is a demo helper: given a base message and a constitution, it simulates
how a Gateway/tool wrapper would enforce disclosure for outbound messaging.

Rules:
- If constitution rule `amendment-I-transparency` specifies:
    require.disclosure.mode == append_if_missing
  then append require.disclosure.text unless the message already contains a
  simple AI disclosure hint.

Usage:
  python scripts/apply_disclosure.py --constitution constitution.yaml --message-file msg.txt
  python scripts/apply_disclosure.py --constitution constitution.yaml --message "hello"

Output:
  Writes the final message to stdout.
"""

from __future__ import annotations

import argparse
import re
import sys
from typing import Any, Dict, Optional

try:
    import yaml  # pyyaml
except ImportError as e:
    raise SystemExit("Missing dependency: pyyaml. Install with: pip install pyyaml") from e


AI_DISCLOSURE_HINT = re.compile(r"\b(ai|assistant|bot)\b", re.I)


def load_disclosure(constitution: Dict[str, Any]) -> Optional[Dict[str, str]]:
    for rule in constitution.get("rules", []) or []:
        if rule.get("id") == "amendment-I-transparency":
            req = rule.get("require") or {}
            disc = req.get("disclosure")
            if isinstance(disc, dict):
                mode = str(disc.get("mode") or "")
                text = str(disc.get("text") or "")
                if mode and text:
                    return {"mode": mode, "text": text}
    return None


def apply(message: str, disclosure: Optional[Dict[str, str]]) -> str:
    if not disclosure:
        return message

    mode = disclosure["mode"]
    text = disclosure["text"]

    if mode == "append_if_missing":
        if AI_DISCLOSURE_HINT.search(message):
            return message
        # Avoid duplicate footer if already present.
        if text.strip() and text.strip() in message:
            return message
        return message + text

    # Unknown modes are no-ops in the demo helper.
    return message


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--constitution", required=True)
    ap.add_argument("--message", default=None)
    ap.add_argument("--message-file", default=None)
    ns = ap.parse_args()

    constitution = yaml.safe_load(open(ns.constitution, "r", encoding="utf-8").read())
    disclosure = load_disclosure(constitution)

    if ns.message_file:
        msg = open(ns.message_file, "r", encoding="utf-8").read()
    elif ns.message is not None:
        msg = ns.message
    else:
        print("Provide --message or --message-file", file=sys.stderr)
        return 2

    sys.stdout.write(apply(msg, disclosure))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
