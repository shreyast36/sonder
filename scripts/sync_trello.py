#!/usr/bin/env python3
"""
Sync TASKS.md checkbox completion → Trello board.

Each card in trello_map.json maps to a list of TASKS.md task keywords.
Completion logic:
  - All matched tasks checked  → moves card to Done
  - Some matched tasks checked → moves card to Doing
  - No matched tasks checked   → leaves card in its current To Do list

Usage:
  python scripts/sync_trello.py

Required env vars:
  TRELLO_API_KEY
  TRELLO_TOKEN
"""

import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

TASKS_FILE = "TASKS.md"
MAP_FILE   = "scripts/trello_map.json"
BASE_URL   = "https://api.trello.com/1"


def trello(method, path, params=None):
    key   = os.environ["TRELLO_API_KEY"]
    token = os.environ["TRELLO_TOKEN"]
    url   = f"{BASE_URL}{path}?key={urllib.parse.quote(key)}&token={urllib.parse.quote(token)}"
    body  = urllib.parse.urlencode(params).encode() if params else None
    req   = urllib.request.Request(url, data=body, method=method)
    try:
        with urllib.request.urlopen(req) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        print(f"  ✗ Trello API error {e.code}: {e.read().decode()}", file=sys.stderr)
        raise


def parse_tasks(path):
    """Return two sets: checked task lines and unchecked task lines."""
    checked, unchecked = set(), set()
    with open(path, encoding="utf-8") as f:
        for line in f:
            m = re.match(r"\s*-\s*\[([xX ])\]\s+(.+)", line)
            if not m:
                continue
            (checked if m.group(1).lower() == "x" else unchecked).add(m.group(2).strip())
    return checked, unchecked


def card_status(keywords, checked, unchecked):
    """Return 'done', 'doing', or 'todo' based on how many keywords match checked tasks."""
    n_checked   = sum(1 for k in keywords if any(k in line for line in checked))
    n_unchecked = sum(1 for k in keywords if any(k in line for line in unchecked))
    total = n_checked + n_unchecked
    if total == 0 or n_checked == 0:
        return "todo"
    if n_checked == total:
        return "done"
    return "doing"


def get_current_list(card_id):
    card = trello("GET", f"/cards/{card_id}")
    return card["idList"]


def main():
    for var in ("TRELLO_API_KEY", "TRELLO_TOKEN"):
        if not os.environ.get(var):
            sys.exit(f"Missing env var: {var}")

    with open(MAP_FILE, encoding="utf-8") as f:
        mapping = json.load(f)

    checked, unchecked = parse_tasks(TASKS_FILE)
    doing_list = mapping["lists"]["doing"]
    done_list  = mapping["lists"]["done"]

    print(f"Parsed {len(checked)} checked and {len(unchecked)} unchecked tasks from {TASKS_FILE}\n")

    moved_count = 0
    for card in mapping["cards"]:
        status     = card_status(card["task_keywords"], checked, unchecked)
        target     = done_list if status == "done" else (doing_list if status == "doing" else None)
        current    = get_current_list(card["id"])

        if target and current != target:
            trello("PUT", f"/cards/{card['id']}", {"idList": target})
            label = "DONE" if status == "done" else "DOING"
            print(f"  ✓ [{label}]  {card['name']}")
            moved_count += 1
        elif target and current == target:
            label = "DONE" if status == "done" else "DOING"
            print(f"  = [{label}]  {card['name']}  (already in correct list)")
        else:
            print(f"  - [TODO]   {card['name']}")

    print(f"\nSync complete — {moved_count} card(s) moved.")


if __name__ == "__main__":
    main()
