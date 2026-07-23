"""
Blue-team investigation script for Kiln & Co.

Scenario: a customer used the "Report a problem" form to say something
looked wrong with their account or order. This script is what an analyst
runs next: it cross-references every request in requests.log against the
REAL ownership data in kiln.db, and flags every case where a logged-in
user accessed or modified an order that wasn't theirs.

This is the same idea as any real detection rule for Broken Object Level
Authorization (IDOR/BOLA, currently #1 on the OWASP API Security Top 10):
you can't tell from a single request whether it's malicious, but you CAN
tell, by comparing the requester's identity to the record's real owner,
whether it was ever authorized at all.

Run this after you've done a live "attack" against the app, so there's
real data in requests.log to analyze.
"""

import json
import re
import sqlite3
from collections import defaultdict

LOG_PATH = "requests.log"
DB_PATH = "kiln.db"

ORDER_PATH_RE = re.compile(r"^/order/(\d+)")


def load_log(path=LOG_PATH):
    entries = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                entries.append(json.loads(line))
    return entries


def load_order_owners(path=DB_PATH):
    db = sqlite3.connect(path)
    rows = db.execute("SELECT id, user_id FROM orders").fetchall()
    db.execute  # no-op, kept explicit for readability
    owners = {order_id: owner_id for order_id, owner_id in rows}
    db.close()
    return owners


def load_usernames(path=DB_PATH):
    db = sqlite3.connect(path)
    rows = db.execute("SELECT id, username FROM users").fetchall()
    db.close()
    return {uid: username for uid, username in rows}


def find_bola_attempts(entries, order_owners, usernames):
    """Flag every request to /order/<id> made by a user who does not own that order."""
    findings = []
    for e in entries:
        match = ORDER_PATH_RE.match(e["path"])
        if not match:
            continue

        order_id = int(match.group(1))
        requester_id = e.get("session_user_id")
        owner_id = order_owners.get(order_id)

        if requester_id is None or owner_id is None:
            continue  # not logged in, or order doesn't exist — not a BOLA case

        if requester_id != owner_id:
            findings.append({
                "time": e["time"],
                "requester": usernames.get(requester_id, f"user #{requester_id}"),
                "order_id": order_id,
                "owner": usernames.get(owner_id, f"user #{owner_id}"),
                "method": e["method"],
                "path": e["path"],
                "ip": e["ip"],
                "is_write": e["method"] == "POST",
            })
    return findings


def find_enumeration_pattern(findings):
    """Flag any single user who touched more than one order they don't own — that's scanning, not a fluke."""
    by_requester = defaultdict(set)
    for f in findings:
        by_requester[f["requester"]].add(f["order_id"])

    enumerators = {user: order_ids for user, order_ids in by_requester.items() if len(order_ids) > 1}
    return enumerators


def main():
    entries = load_log()
    order_owners = load_order_owners()
    usernames = load_usernames()

    print(f"Loaded {len(entries)} log entries and {len(order_owners)} known orders.\n")

    findings = find_bola_attempts(entries, order_owners, usernames)

    print("=== Broken Object Level Authorization (IDOR) findings ===")
    if not findings:
        print("None found. Either nothing happened, or nothing has been logged yet.")
    for f in findings:
        action = "MODIFIED" if f["is_write"] else "VIEWED"
        print(
            f"[{f['time']}] {f['requester']} {action} order #{f['order_id']} "
            f"(belongs to {f['owner']}) via {f['method']} {f['path']} from {f['ip']}"
        )

    print("\n=== Enumeration pattern (same user touching multiple orders they don't own) ===")
    enumerators = find_enumeration_pattern(findings)
    if not enumerators:
        print("None found.")
    for user, order_ids in enumerators.items():
        print(f"{user} accessed {len(order_ids)} orders that don't belong to them: {sorted(order_ids)}")
        print("  -> This pattern (one identity, several other people's records) is what separates a")
        print("     genuine authorization bug report from someone systematically scraping data.")


if __name__ == "__main__":
    main()
