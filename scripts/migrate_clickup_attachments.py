#!/usr/bin/env python3
"""Copy ClickUp task attachments onto their matching, already-imported Vikunja tasks.

Matching key: tasks imported from ClickUp keep the ClickUp task id as a
"[clickup_id] Title" prefix (e.g. "[868kdek62] Agents gateway"). Tasks without
that prefix (created directly in Vikunja) are skipped.

Safe to re-run: every successful upload is recorded in a local ledger
(~/.config/vikunja-clickup-migration/ledger.json) keyed by ClickUp's own
attachment id, and already-recorded attachments are skipped. A ClickUp id is
used rather than the Vikunja-side filename because many attachments across
these tasks share the same generic name (e.g. "image.png" appears multiple
times on a single task for pasted screenshots) - a filename-only check would
wrongly skip real, distinct files. Trade-off: delete the ledger and re-run
on a task that was already migrated, and its attachments get re-uploaded as
duplicates (untidy, not silent data loss - the opposite failure mode is
worse). Only reads happen against ClickUp; only reads + attachment uploads
happen against Vikunja - nothing is deleted or overwritten there.

Setup:
    1. In Vikunja (Settings > API Tokens) create a new token with:
       - Tasks: Read all
       - Task attachments: Read all, Create
    2. export VIKUNJA_TOKEN=<that token>
       export CLICKUP_TOKEN=<clickup personal token>   (or reuse ~/.config/clickup/token)
       export VIKUNJA_BASE=https://tasks.docsales.com/api/v1   (default, override if needed)

Usage:
    python3 scripts/migrate_clickup_attachments.py --dry-run          # preview only, no uploads
    python3 scripts/migrate_clickup_attachments.py --task-id 1        # test on a single Vikunja task
    python3 scripts/migrate_clickup_attachments.py                    # full run

Re-run any time (e.g. after a later ClickUp import) - already-uploaded files are skipped.
"""
import argparse
import json
import mimetypes
import os
import re
import sys
import time
import urllib.error
import urllib.request
import uuid

VIKUNJA_BASE = os.environ.get("VIKUNJA_BASE", "https://tasks.docsales.com/api/v1")
CLICKUP_BASE = "https://api.clickup.com/api/v2"
TITLE_RE = re.compile(r"^\[([A-Za-z0-9_-]+)\]\s*")
LOG_PATH = os.path.expanduser("~/.config/vikunja-clickup-migration/progress.log")
LEDGER_PATH = os.path.expanduser("~/.config/vikunja-clickup-migration/ledger.json")
# Railway's edge blocks the default urllib/Python User-Agent as bot traffic (403);
# any non-default UA string clears it.
USER_AGENT = "docsales-vikunja-clickup-migration/1.0"


def read_token(env_name, file_path):
    token = os.environ.get(env_name)
    if token:
        return token.strip()
    if file_path and os.path.exists(file_path):
        with open(file_path) as f:
            return f.read().strip()
    return None


VIKUNJA_TOKEN = read_token("VIKUNJA_TOKEN", None)
CLICKUP_TOKEN = read_token("CLICKUP_TOKEN", os.path.expanduser("~/.config/clickup/token"))


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


def vikunja_get(path, headers_extra=None):
    headers = {"Authorization": f"Bearer {VIKUNJA_TOKEN}"}
    headers.update(headers_extra or {})
    return http_json(f"{VIKUNJA_BASE}{path}", headers)


def list_all_vikunja_tasks():
    tasks = []
    page = 1
    while True:
        req = urllib.request.Request(
            f"{VIKUNJA_BASE}/tasks?page={page}&per_page=50",
            headers={"Authorization": f"Bearer {VIKUNJA_TOKEN}", "User-Agent": USER_AGENT},
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            batch = json.loads(resp.read())
            total_pages = int(resp.headers.get("x-pagination-total-pages", "1"))
        tasks.extend(batch)
        if page >= total_pages or not batch:
            break
        page += 1
    return tasks


def clickup_get_task(clickup_id):
    headers = {"Authorization": CLICKUP_TOKEN}
    return http_json(f"{CLICKUP_BASE}/task/{clickup_id}", headers)


def download(url):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return resp.read()


def upload_attachment(task_id, filename, data):
    boundary = uuid.uuid4().hex
    mime = mimetypes.guess_type(filename)[0] or "application/octet-stream"
    body = b""
    body += f"--{boundary}\r\n".encode()
    body += f'Content-Disposition: form-data; name="files"; filename="{filename}"\r\n'.encode()
    body += f"Content-Type: {mime}\r\n\r\n".encode()
    body += data
    body += f"\r\n--{boundary}--\r\n".encode()

    req = urllib.request.Request(
        f"{VIKUNJA_BASE}/tasks/{task_id}/attachments",
        method="PUT",
        data=body,
        headers={
            "Authorization": f"Bearer {VIKUNJA_TOKEN}",
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "User-Agent": USER_AGENT,
        },
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        return json.loads(resp.read())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="preview only, no uploads")
    parser.add_argument("--task-id", type=int, help="only process this Vikunja task id")
    args = parser.parse_args()

    if not VIKUNJA_TOKEN:
        sys.exit("Set VIKUNJA_TOKEN (scoped: tasks:read_all, task_attachments:read_all+create)")
    if not CLICKUP_TOKEN:
        sys.exit("Set CLICKUP_TOKEN (or place it at ~/.config/clickup/token)")

    log(f"=== run started, dry_run={args.dry_run}, task_id={args.task_id} ===")

    ledger = load_ledger()

    if args.task_id:
        tasks = [vikunja_get(f"/tasks/{args.task_id}")]
    else:
        tasks = list_all_vikunja_tasks()

    matched, with_attachments, uploaded, skipped, failed = 0, 0, 0, 0, 0

    for task in tasks:
        m = TITLE_RE.match(task["title"])
        if not m:
            continue
        matched += 1
        clickup_id = m.group(1)

        try:
            cu_task = clickup_get_task(clickup_id)
        except urllib.error.HTTPError as e:
            log(f"[task {task['id']}] ClickUp task {clickup_id} fetch failed: {e}")
            failed += 1
            continue

        attachments = (cu_task or {}).get("attachments") or []
        if not attachments:
            continue
        with_attachments += 1

        for att in attachments:
            att_id = str(att["id"])
            filename = att.get("title") or f"{att_id}.{att.get('extension', 'bin')}"

            if att_id in ledger:
                log(f"[task {task['id']}] skip (already migrated): {filename}")
                skipped += 1
                continue

            if args.dry_run:
                log(f"[task {task['id']}] would upload: {filename} (clickup {clickup_id})")
                continue

            try:
                data = download(att["url"])
                upload_attachment(task["id"], filename, data)
                ledger[att_id] = {
                    "vikunja_task_id": task["id"],
                    "clickup_task_id": clickup_id,
                    "filename": filename,
                }
                save_ledger(ledger)
                log(f"[task {task['id']}] uploaded: {filename}")
                uploaded += 1
                time.sleep(0.3)
            except Exception as e:
                log(f"[task {task['id']}] FAILED to upload {filename}: {e}")
                failed += 1

    log(
        f"=== done: {len(tasks)} tasks scanned, {matched} matched a ClickUp id, "
        f"{with_attachments} had attachments, {uploaded} uploaded, "
        f"{skipped} already present, {failed} failed ==="
    )


if __name__ == "__main__":
    main()
