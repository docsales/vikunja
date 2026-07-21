#!/usr/bin/env python3
"""Reimport every currently-open ClickUp task into Vikunja, with project and
assignee mapping resolved from the current, definitive user/project set.

Safe to re-run: every created task is recorded in a local ledger
(~/.config/vikunja-clickup-migration/reimport_ledger.json) keyed by ClickUp's
task id, and already-imported tasks are skipped.

Setup:
    export VIKUNJA_TOKEN=<full-access token>
    export CLICKUP_TOKEN=<clickup personal token>   (or reuse ~/.config/clickup/token)

Usage:
    python3 scripts/reimport_clickup_tasks.py --dry-run
    python3 scripts/reimport_clickup_tasks.py --limit 1     # sanity-check one task end to end
    python3 scripts/reimport_clickup_tasks.py               # full run
"""
import argparse
import datetime
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request

VIKUNJA_BASE = os.environ.get("VIKUNJA_BASE", "https://tasks.docsales.com/api/v1")
CLICKUP_BASE = "https://api.clickup.com/api/v2"
TEAM_ID = "9011545097"
USER_AGENT = "docsales-vikunja-clickup-migration/1.0"
LEDGER_PATH = os.path.expanduser("~/.config/vikunja-clickup-migration/reimport_ledger.json")
LOG_PATH = os.path.expanduser("~/.config/vikunja-clickup-migration/reimport_progress.log")

# ClickUp email -> Vikunja user id. Gustavo has no Vikunja account yet, so his
# tasks land on Mauricio until he logs in and they get manually reassigned.
EMAIL_TO_VIKUNJA_ID = {
    "jessica@docsales.com": 51,
    "jhonatandasilva2405@gmail.com": 54,
    "mauricio@docsales.com": 1,
    "daniel@docsales.com": 52,
    "joice@docsales.com": 16,
    "tatiane.gomes@docsales.com": 50,
    "victor@docsales.com": 15,
    "adrian@docsales.com": 17,
    "marcelo.medeiros@docsales.com": 14,
    "marcelo.marques@docsales.com": 53,
    "gustavo.arnaldo@reev.co": 1,
}
# Rafael has no Vikunja account and isn't getting the Gustavo treatment: drop
# just his assignment, keep the task and any co-assignees.
EXCLUDED_EMAILS = {"rafael@docsales.com"}

# ClickUp List name -> Vikunja project id. The 4 "Shared with me" lists are
# content shared in from outside DocSales's own space; by instruction they
# fold into Growth & GTM (19) rather than getting their own project.
LIST_TO_PROJECT = {
    "Desenvolvimento": 20,
    "Demandas - Clientes & Time": 21,
    "Suporte técnico": 22,
    "Ativações": 23,
    "Cancelamento": 24,
    "WhatsAudio": 25,
    "Franquias": 26,
    "Contratos imob": 27,
    "Granasim": 28,
    "Growth & GTM": 19,
    "List": 29,
    "P & G": 19,
    "Ações - Docsales": 19,
    "Ações - ContratosImob": 19,
    "Shared with me": 19,
}

PRIORITY_MAP = {"low": 1, "normal": 2, "high": 3, "urgent": 4}

VIKUNJA_TOKEN = os.environ.get("VIKUNJA_TOKEN")
CLICKUP_TOKEN = os.environ.get("CLICKUP_TOKEN") or (
    open(os.path.expanduser("~/.config/clickup/token")).read().strip()
    if os.path.exists(os.path.expanduser("~/.config/clickup/token")) else None
)


def log(msg):
    print(msg)
    os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
    with open(LOG_PATH, "a") as f:
        f.write(f"{msg}\n")


def load_ledger():
    if os.path.exists(LEDGER_PATH):
        with open(LEDGER_PATH) as f:
            return json.load(f)
    return {}


def save_ledger(ledger):
    os.makedirs(os.path.dirname(LEDGER_PATH), exist_ok=True)
    with open(LEDGER_PATH, "w") as f:
        json.dump(ledger, f, indent=2, sort_keys=True)


def http_json(url, headers, method="GET", data=None, retries=3):
    headers = {"User-Agent": USER_AGENT, **headers}
    for attempt in range(retries):
        req = urllib.request.Request(url, method=method, headers=headers, data=data)
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                body = resp.read()
                return json.loads(body) if body else None
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < retries - 1:
                wait = int(e.headers.get("Retry-After", "5"))
                log(f"  rate limited, waiting {wait}s...")
                time.sleep(wait)
                continue
            raise
    return None


def clickup_list_all_open_tasks():
    tasks, page = [], 0
    while True:
        url = f"{CLICKUP_BASE}/team/{TEAM_ID}/task?archived=false&subtasks=true&include_closed=false&page={page}"
        data = http_json(url, {"Authorization": CLICKUP_TOKEN})
        batch = data.get("tasks", [])
        tasks.extend(batch)
        if data.get("last_page", True) or not batch:
            break
        page += 1
    return tasks


def to_rfc3339(epoch_ms):
    if not epoch_ms:
        return None
    dt = datetime.datetime.fromtimestamp(int(epoch_ms) / 1000, tz=datetime.timezone.utc)
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def vikunja_create_task(project_id, payload):
    body = json.dumps(payload).encode()
    return http_json(
        f"{VIKUNJA_BASE}/projects/{project_id}/tasks",
        {"Authorization": f"Bearer {VIKUNJA_TOKEN}", "Content-Type": "application/json"},
        method="PUT", data=body,
    )


def vikunja_set_assignees(task_id, user_ids):
    body = json.dumps({"assignees": [{"id": uid} for uid in user_ids]}).encode()
    return http_json(
        f"{VIKUNJA_BASE}/tasks/{task_id}/assignees/bulk",
        {"Authorization": f"Bearer {VIKUNJA_TOKEN}", "Content-Type": "application/json"},
        method="POST", data=body,
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--limit", type=int, help="only process the first N tasks (sanity check)")
    args = parser.parse_args()

    if not VIKUNJA_TOKEN:
        sys.exit("Set VIKUNJA_TOKEN")
    if not CLICKUP_TOKEN:
        sys.exit("Set CLICKUP_TOKEN")

    log(f"=== reimport started, dry_run={args.dry_run}, limit={args.limit} ===")

    tasks = clickup_list_all_open_tasks()
    log(f"fetched {len(tasks)} open ClickUp tasks")
    if args.limit:
        tasks = tasks[:args.limit]

    ledger = load_ledger()
    created, skipped_existing, skipped_unmapped_list, failed, unknown_assignees = 0, 0, 0, 0, set()

    for task in tasks:
        cid = task["id"]
        if cid in ledger:
            skipped_existing += 1
            continue

        list_name = task.get("list", {}).get("name")
        project_id = LIST_TO_PROJECT.get(list_name)
        if project_id is None:
            log(f"[clickup {cid}] SKIP: unmapped list {list_name!r} - {task['name'][:50]!r}")
            skipped_unmapped_list += 1
            continue

        assignee_ids = []
        for a in task.get("assignees", []):
            email = a["email"]
            if email in EXCLUDED_EMAILS:
                continue
            uid = EMAIL_TO_VIKUNJA_ID.get(email)
            if uid:
                if uid not in assignee_ids:
                    assignee_ids.append(uid)
            else:
                unknown_assignees.add(email)

        priority = PRIORITY_MAP.get((task.get("priority") or {}).get("priority"), 0)
        due_date = to_rfc3339(task.get("due_date"))
        title = f"[{cid}] {task['name']}"
        description = task.get("description") or ""

        if args.dry_run:
            log(f"[clickup {cid}] would create in project {project_id}, assignees={assignee_ids}: {title[:70]!r}")
            continue

        payload = {"title": title, "description": description, "priority": priority}
        if due_date:
            payload["due_date"] = due_date

        try:
            new_task = vikunja_create_task(project_id, payload)
            new_task_id = new_task["id"]
            ledger[cid] = new_task_id
            save_ledger(ledger)

            if assignee_ids:
                vikunja_set_assignees(new_task_id, assignee_ids)

            log(f"[clickup {cid}] created as vikunja task {new_task_id} in project {project_id}, assignees={assignee_ids}")
            created += 1
            time.sleep(0.2)
        except Exception as e:
            log(f"[clickup {cid}] FAILED: {e}")
            failed += 1

    log(
        f"=== done: {len(tasks)} scanned, {created} created, {skipped_existing} already imported, "
        f"{skipped_unmapped_list} skipped (unmapped list), {failed} failed ==="
    )
    if unknown_assignees:
        log(f"unknown assignee emails seen (not mapped, not excluded): {sorted(unknown_assignees)}")


if __name__ == "__main__":
    main()
