#!/usr/bin/env python3
"""CLI tool to approve or deny agent approval requests.

Usage:
    python oc-approve.py approve apv-20260323080000-12345
    python oc-approve.py deny apv-20260323080000-12345
    python oc-approve.py list                              # show pending
"""
import json
import os
import sys
import glob

APPROVALS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "logs", "approvals"
)


def list_pending():
    """List all pending approval requests."""
    pattern = os.path.join(APPROVALS_DIR, "apv-*.json")
    pending = []
    for path in sorted(glob.glob(pattern)):
        try:
            with open(path, "r", encoding="utf-8") as f:
                record = json.load(f)
            if record.get("status") == "pending":
                pending.append(record)
        except Exception:
            pass

    if not pending:
        print("No pending approvals.")
        return

    for r in pending:
        print(f"  {r['approvalId']}  tool={r['toolName']}  risk={r['risk']}  requested={r['requestedAt']}")


def decide(apv_id: str, status: str):
    """Approve or deny a request."""
    # Add agent dir to path for import
    agent_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "agent")
    sys.path.insert(0, agent_dir)
    from services.approval_service import approve, deny

    if status == "approved":
        ok = approve(apv_id)
    else:
        ok = deny(apv_id)

    if ok:
        print(f"{status.upper()}: {apv_id}")
    else:
        print(f"Failed: {apv_id} not found or already decided.")
        sys.exit(1)


def main():
    if len(sys.argv) < 2:
        print("Usage: oc-approve.py <approve|deny|list> [apv-id]")
        sys.exit(2)

    action = sys.argv[1].lower()

    if action == "list":
        list_pending()
    elif action in ("approve", "yes", "onayla"):
        if len(sys.argv) < 3:
            print("Usage: oc-approve.py approve <apv-id>")
            sys.exit(2)
        decide(sys.argv[2], "approved")
    elif action in ("deny", "no", "reddet"):
        if len(sys.argv) < 3:
            print("Usage: oc-approve.py deny <apv-id>")
            sys.exit(2)
        decide(sys.argv[2], "denied")
    else:
        print(f"Unknown action: {action}")
        sys.exit(2)


if __name__ == "__main__":
    main()
