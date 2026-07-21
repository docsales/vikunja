#!/usr/bin/env python3
"""Emergency recovery: restores description, priority, due_date and assignees
on all 418 reimported tasks, which got wiped by a title-only update call
(POST /tasks/:id with a partial body clears every field it doesn't receive,
including assignees via updateTaskAssignees(s, t.Assignees, a) - see
pkg/models/tasks.go's updateSingleTask). Labels, attachments and subtask
relations are untouched by that endpoint and were not affected.

Safe to re-run: recomputes every field from the ClickUp source data and the
reimport ledger each time, so it's idempotent.

Usage:
    export VIKUNJA_TOKEN=<full-access token>
    python3 scripts/restore_wiped_task_fields.py
"""
import datetime
import json
import os
import sys
import urllib.error
import urllib.request

VIKUNJA_BASE = os.environ.get("VIKUNJA_BASE", "https://tasks.docsales.com/api/v1")
USER_AGENT = "docsales-vikunja-clickup-migration/1.0"
VIKUNJA_TOKEN = os.environ.get("VIKUNJA_TOKEN")
LEDGER_PATH = os.path.expanduser("~/.config/vikunja-clickup-migration/reimport_ledger.json")
CLICKUP_DUMP = "/private/tmp/claude-501/-Users-mauriciokigiela-Documents-git-tasks/8e5b4fdf-3e21-45b8-8be3-11c0e25e7ec4/scratchpad/clickup_all_open_tasks.json"

# Gustavo and Rafael now have real accounts (56, 58) - this is the corrected
# mapping, not the original reimport's placeholder-on-Mauricio one.
EMAIL_TO_VIKUNJA_ID = {
    "jessica@docsales.com": 51, "jhonatandasilva2405@gmail.com": 54, "mauricio@docsales.com": 1,
    "daniel@docsales.com": 52, "joice@docsales.com": 16, "tatiane.gomes@docsales.com": 50,
    "victor@docsales.com": 15, "adrian@docsales.com": 17, "marcelo.medeiros@docsales.com": 14,
    "marcelo.marques@docsales.com": 53, "gustavo.arnaldo@reev.co": 56, "rafael@docsales.com": 58,
}
PRIORITY_MAP = {"low": 1, "normal": 2, "high": 3, "urgent": 4}


def to_rfc3339(epoch_ms):
    if not epoch_ms:
        return None
    dt = datetime.datetime.fromtimestamp(int(epoch_ms) / 1000, tz=datetime.timezone.utc)
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def http_json(url, method="GET", data=None):
    headers = {"Authorization": f"Bearer {VIKUNJA_TOKEN}", "User-Agent": USER_AGENT,
               "Content-Type": "application/json"}
    req = urllib.request.Request(url, method=method, headers=headers, data=data)
    with urllib.request.urlopen(req, timeout=30) as resp:
        body = resp.read()
        return json.loads(body) if body else None


def main():
    if not VIKUNJA_TOKEN:
        sys.exit("Set VIKUNJA_TOKEN")

    ledger = json.load(open(LEDGER_PATH))
    with open(CLICKUP_DUMP) as f:
        clickup_tasks = {t["id"]: t for t in json.load(f)}

    fixed, failed = 0, 0
    for cid, vid in ledger.items():
        ct = clickup_tasks.get(cid)
        if not ct:
            print(f"WARNING: no ClickUp source for {cid} (vikunja {vid}), skipping")
            continue

        current = http_json(f"{VIKUNJA_BASE}/tasks/{vid}")

        assignee_ids = []
        for a in ct.get("assignees", []):
            uid = EMAIL_TO_VIKUNJA_ID.get(a["email"])
            if uid and uid not in assignee_ids:
                assignee_ids.append(uid)

        priority = PRIORITY_MAP.get((ct.get("priority") or {}).get("priority"), 0)
        due_date = to_rfc3339(ct.get("due_date"))
        description = ct.get("description") or ""

        payload = {
            "title": current["title"],
            "description": description,
            "priority": priority,
            "assignees": [{"id": i} for i in assignee_ids],
        }
        if due_date:
            payload["due_date"] = due_date

        try:
            http_json(f"{VIKUNJA_BASE}/tasks/{vid}", method="POST", data=json.dumps(payload).encode())
            fixed += 1
        except urllib.error.HTTPError as e:
            print(f"FAILED task {vid} (clickup {cid}): {e} {e.read().decode()[:200]}")
            failed += 1

    print(f"done: {fixed} restored, {failed} failed")


if __name__ == "__main__":
    main()
