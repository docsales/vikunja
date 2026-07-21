#!/usr/bin/env python3
"""Backfill labels (from ClickUp tags) and subtask/parent relations onto the
already-reimported tasks. Uses the reimport ledger (clickup_id -> vikunja
task_id) so it only needs to run once, after the reimport, against the same
ClickUp task dump.
"""
import json
import os
import sys
import time
import urllib.error
import urllib.request

VIKUNJA_BASE = os.environ.get("VIKUNJA_BASE", "https://tasks.docsales.com/api/v1")
USER_AGENT = "docsales-vikunja-clickup-migration/1.0"
VIKUNJA_TOKEN = os.environ.get("VIKUNJA_TOKEN")
LEDGER_PATH = os.path.expanduser("~/.config/vikunja-clickup-migration/reimport_ledger.json")
LOG_PATH = os.path.expanduser("~/.config/vikunja-clickup-migration/backfill_labels_subtasks.log")
CLICKUP_DUMP = "/private/tmp/claude-501/-Users-mauriciokigiela-Documents-git-tasks/8e5b4fdf-3e21-45b8-8be3-11c0e25e7ec4/scratchpad/clickup_all_open_tasks.json"

LABEL_NAME_TO_ID = {
    "cancelamento": 1, "bug": 2, "bug geral": 3, "débito técnico": 4,
    "priorizado": 5, "ativação": 6, "melhoria interna": 7,
    "new feature/int.": 8, "definição de produto": 9, "aguardando": 10,
}


def log(msg):
    print(msg)
    os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
    with open(LOG_PATH, "a") as f:
        f.write(f"{msg}\n")


def http_json(url, method="GET", data=None, retries=3):
    headers = {"Authorization": f"Bearer {VIKUNJA_TOKEN}", "User-Agent": USER_AGENT,
               "Content-Type": "application/json"}
    for attempt in range(retries):
        req = urllib.request.Request(url, method=method, headers=headers, data=data)
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                body = resp.read()
                return json.loads(body) if body else None
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < retries - 1:
                time.sleep(int(e.headers.get("Retry-After", "5")))
                continue
            raise
    return None


def add_label(task_id, label_id):
    body = json.dumps({"label_id": label_id}).encode()
    return http_json(f"{VIKUNJA_BASE}/tasks/{task_id}/labels", method="PUT", data=body)


def add_parent_relation(child_task_id, parent_task_id):
    body = json.dumps({"other_task_id": parent_task_id, "relation_kind": "parenttask"}).encode()
    return http_json(f"{VIKUNJA_BASE}/tasks/{child_task_id}/relations", method="PUT", data=body)


def main():
    if not VIKUNJA_TOKEN:
        sys.exit("Set VIKUNJA_TOKEN")

    with open(CLICKUP_DUMP) as f:
        clickup_tasks = {t["id"]: t for t in json.load(f)}
    ledger = json.load(open(LEDGER_PATH))

    log("=== labels ===")
    labels_added, labels_failed, unknown_tags = 0, 0, set()
    for clickup_id, vikunja_task_id in ledger.items():
        task = clickup_tasks.get(clickup_id)
        if not task:
            continue
        for tag in task.get("tags", []):
            name = tag["name"]
            label_id = LABEL_NAME_TO_ID.get(name)
            if not label_id:
                unknown_tags.add(name)
                continue
            try:
                add_label(vikunja_task_id, label_id)
                labels_added += 1
            except Exception as e:
                log(f"[clickup {clickup_id}] vikunja {vikunja_task_id}: label {name!r} FAILED: {e}")
                labels_failed += 1
    log(f"labels added: {labels_added}, failed: {labels_failed}, unknown tag names: {sorted(unknown_tags)}")

    log("\n=== subtask relations ===")
    linked, parent_not_imported, failed = 0, 0, 0
    for clickup_id, vikunja_task_id in ledger.items():
        task = clickup_tasks.get(clickup_id)
        if not task or not task.get("parent"):
            continue
        parent_clickup_id = task["parent"]
        parent_vikunja_id = ledger.get(parent_clickup_id)
        if not parent_vikunja_id:
            log(f"[clickup {clickup_id}] parent {parent_clickup_id} not in ledger (closed/not imported) - skipping")
            parent_not_imported += 1
            continue
        try:
            add_parent_relation(vikunja_task_id, parent_vikunja_id)
            log(f"[clickup {clickup_id}] vikunja {vikunja_task_id} linked as subtask of vikunja {parent_vikunja_id}")
            linked += 1
            time.sleep(0.1)
        except Exception as e:
            log(f"[clickup {clickup_id}] relation FAILED: {e}")
            failed += 1

    log(f"\n=== done: {linked} subtask relations linked, {parent_not_imported} parents not imported, {failed} failed ===")


if __name__ == "__main__":
    main()
