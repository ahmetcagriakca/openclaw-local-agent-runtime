#!/usr/bin/env python3
"""CLI audit chain verifier — D-129.

Usage: python tools/verify-audit-chain.py [path]
Default path: logs/audit/audit.jsonl

Exit code 0 = INTEGRITY_OK
Exit code 1 = INTEGRITY_FAIL or error
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "agent"))

from persistence.audit_integrity import verify_chain

def main():
    path = sys.argv[1] if len(sys.argv) > 1 else None
    result = verify_chain(path)

    if result["status"] == "INTEGRITY_OK":
        print(f"INTEGRITY_OK entry_count={result['entry_count']}")
        sys.exit(0)
    else:
        print(f"INTEGRITY_FAIL broken_entry_index={result['broken_entry_index']} reason={result['reason']}")
        sys.exit(1)

if __name__ == "__main__":
    main()
