#!/usr/bin/env python3
"""
Sync TASKS.md sections → Trello board.

Creates one Trello card per TASKS.md section (e.g. "Jahnvi: Frontend Screens").
Moves cards to Done / Doing / the person's To Do list based on checkbox completion.

Usage:
  python scripts/sync_trello.py

Required env vars:
  TRELLO_API_KEY
  TRELLO_TOKEN

Optional env vars:
  TRELLO_BOARD_ID   (default: 1GooiYMd)
"""

import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

TASKS_FILE = "TASKS.md"
BOARD_ID   = os.environ.get("TRELLO_BOARD_ID", "1GooiYMd")
BASE_URL   = "https://api.trello.com/1"

# Keywords to find each person's To Do list (matched case-insensitively against list name)
PERSON_LIST_KEYWORDS = {
    "Shreyas":  ["shreyas"],
    "Jahnvi":   ["janvi", "jahnvi"],
    "Mushahid": ["mushahid", "mushaid"],
    "Ali":      ["ali"],
}

DOING_KEYWORDS = ["doing"]
DONE_KEYWORDS  = ["done"]


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


def find_list(lists, keywords):
    """Return the first list ID whose name contains any keyword (case-insensitive)."""
    for lst in lists:
        if any(kw in lst["name"].lower() for kw in keywords):
            return lst["id"]
    return None


def parse_sections(path):
    """
    Parse TASKS.md into sections by H2 (person) and H3 (subsection).
    Returns list of dicts: {person, subsection, card_name, checked, total}
    """
    sections = []
    current_person = None
    current_sub    = None
    checked = total = 0

    def flush():
        if current_person and current_sub:
            sections.append({
                "person":     current_person,
                "subsection": current_sub,
                "card_name":  f"{current_person}: {current_sub}",
                "checked":    checked,
                "total":      total,
            })

    with open(path, encoding="utf-8") as f:
        for line in f:
            # H2 = person  (e.g. "## Jahnvi — Lead Product...")
            m = re.match(r"^## (.+?) —", line)
            if m:
                flush()
                current_person = m.group(1).strip()
                current_sub    = None
                checked = total = 0
                continue

            # H3 = subsection  (e.g. "### Frontend — Screens")
            m = re.match(r"^### (.+)", line)
            if m:
                flush()
                current_sub = m.group(1).strip()
                checked = total = 0
                continue

            # Checkbox line
            m = re.match(r"\s*-\s*\[([xX ])\]", line)
            if m and current_sub:
                total += 1
                if m.group(1).lower() == "x":
                    checked += 1

    flush()
    return sections


def card_status(checked, total):
    if total == 0 or checked == 0:
        return "todo"
    if checked == total:
        return "done"
    return "doing"


def main():
    for var in ("TRELLO_API_KEY", "TRELLO_TOKEN"):
        if not os.environ.get(var):
            sys.exit(f"Missing env var: {var}")

    # --- Discover lists ---
    lists = trello("GET", f"/boards/{BOARD_ID}/lists")

    doing_list = find_list(lists, DOING_KEYWORDS)
    done_list  = find_list(lists, DONE_KEYWORDS)

    person_lists = {
        person: find_list(lists, keywords)
        for person, keywords in PERSON_LIST_KEYWORDS.items()
    }

    print("Lists found:")
    for person, lid in person_lists.items():
        status = lid or "NOT FOUND"
        print(f"  {person}: {status}")
    print(f"  Doing:    {doing_list or 'NOT FOUND'}")
    print(f"  Done:     {done_list  or 'NOT FOUND'}\n")

    missing = [k for k, v in {**person_lists, "Doing": doing_list, "Done": done_list}.items() if not v]
    if missing:
        sys.exit(f"Could not find lists for: {', '.join(missing)}\nCheck list names on the board match keywords.")

    # --- Fetch existing cards (matched by name so we don't duplicate) ---
    all_cards   = trello("GET", f"/boards/{BOARD_ID}/cards")
    card_by_name = {c["name"]: c for c in all_cards}

    # --- Parse TASKS.md ---
    sections = parse_sections(TASKS_FILE)
    print(f"Parsed {len(sections)} sections from {TASKS_FILE}\n")

    created = moved = skipped = 0

    for sec in sections:
        name   = sec["card_name"]
        status = card_status(sec["checked"], sec["total"])
        label  = status.upper()
        prog   = f"{sec['checked']}/{sec['total']}"

        if status == "done":
            target = done_list
        elif status == "doing":
            target = doing_list
        else:
            target = person_lists[sec["person"]]

        if name not in card_by_name:
            new_card = trello("POST", "/cards", {"name": name, "idList": target})
            card_by_name[name] = new_card
            print(f"  + [{label}]  {name}  ({prog}) — created")
            created += 1
        else:
            card    = card_by_name[name]
            current = card["idList"]
            if current != target:
                trello("PUT", f"/cards/{card['id']}", {"idList": target})
                print(f"  ✓ [{label}]  {name}  ({prog}) — moved")
                moved += 1
            else:
                print(f"  = [{label}]  {name}  ({prog}) — already correct")
                skipped += 1

    print(f"\nSync complete — {created} created, {moved} moved, {skipped} already correct.")


if __name__ == "__main__":
    main()
