#!/usr/bin/env python3
"""Preflight dispatch policy or memo source checks before Council root sealing.

Usage: python3 validate_council_source_checks.py packet.json memo.json
This is not a full packet or memo validator; run the complete Council validator.
The host tool trace still needs a separate readback; memo text cannot prove a call.
"""

import argparse
import hashlib
import json
from pathlib import Path

from validate_council_run import _nonempty_string, validate_source_checks


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("packet", type=Path)
    parser.add_argument("memo", type=Path, nargs="?", help="omit for dispatch preflight")
    args = parser.parse_args()
    packet_bytes = args.packet.read_bytes()
    packet = json.loads(packet_bytes)
    if not isinstance(packet, dict) or packet.get("schema_version") != "council-premodel-seat-packet-v4" or packet.get("search_required") is not True:
        print("FAIL: new dispatch requires a blind v4 packet with search_required=true")
        return 1
    if not _nonempty_string(packet.get("instructions")):
        print("FAIL: packet.instructions must be a non-empty string")
        return 1
    if args.memo is None:
        print("PASS: dispatch search policy and instructions declared; verify source tools in the actual seat separately")
        return 0
    memo = json.loads(args.memo.read_bytes())
    errors = validate_source_checks(packet, memo)
    if not isinstance(memo, dict) or memo.get("packet_sha256") != hashlib.sha256(packet_bytes).hexdigest():
        errors.append("memo.packet_sha256 must bind the exact packet bytes")
    if not isinstance(packet, dict) or not isinstance(memo, dict) or memo.get("seat") != packet.get("seat"):
        errors.append("memo.seat must equal packet.seat")
    for error in errors:
        print(f"FAIL: {error}")
    if errors:
        return 1
    print("PASS: opt-in source checks are structurally valid; compare host tool trace separately")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
