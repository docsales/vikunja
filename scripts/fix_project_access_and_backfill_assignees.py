#!/usr/bin/env python3
"""One-off remediation for the reimport: share each project with exactly the
users who have assigned tasks there (read+write), then retry assignee-setting
on every reimported task using the reimport ledger (clickup_id -> vikunja
task_id) plus the same ClickUp assignee data the reimport used.

Needed because most projects had no team/user sharing at all, so the
assignees/bulk call in the initial reimport 403'd for every non-owner user
(the task itself was still created fine - only the assignment step failed).
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
LOG_PATH = os.path.expanduser("~/.config/vikunja-clickup-migration/fix_access_progress.log")
CLICKUP_DUMP = "/private/tmp/claude-501/-Users-mauriciokigiela-Documents-git-tasks/8e5b4fdf-3e21-45b8-8be3-11c0e25e7ec4/scratchpad/clickup_all_open_tasks.json"

EMAIL_TO_VIKUNJA_ID = {
    "jessica@docsales.com": 51, "jhonatandasilva2405@gmail.com": 54,
    "mauricio@docsales.com": 1, "daniel@docsales.com": 52, "joice@docsales.com": 16,
    "tatiane.gomes@docsales.com": 50, "victor@docsales.com": 15, "adrian@docsales.com": 17,
    "marcelo.medeiros@docsales.com": 14, "marcelo.marques@docsales.com": 53,
    "gustavo.arnaldo@reev.co": 1,
}
EXCLUDED_EMAILS = {"rafael@docsales.com"}

LIST_TO_PROJECT = {
    "Desenvolvimento": 20, "Demandas - Clientes & Time": 21, "Suporte técnico": 22,
    "Ativações": 23, "Cancelamento": 24, "WhatsAudio": 25, "Franquias": 26,
    "Contratos imob": 27, "Granasim": 28, "Growth & GTM": 19, "List": 29,
    "P & G": 19, "Ações - Docsales": 19, "Ações - ContratosImob": 19, "Shared with me": 19,
}

NEEDED_SHARES = {
    19: ["adrian", "daniel", "jessica", "jhonatan.silva", "joice", "marcelo.marques", "marcelo.medeiros", "victor"],
    20: ["adrian", "daniel", "marcelo.marques"],
    21: ["daniel", "marcelo.marques", "marcelo.medeiros", "victor"],
    22: ["adrian", "daniel", "joice", "marcelo.marques", "marcelo.medeiros", "victor"],
    23: ["tatiane.gomes"],
    24: ["jessica", "tatiane.gomes"],
    29: ["jhonatan.silva", "marcelo.marques"],
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


def share_project_with_user(project_id, username):
    body = json.dumps({"username": username, "permission": 1}).encode()
    return http_json(f"{VIKUNJA_BASE}/projects/{project_id}/users", method="PUT", data=body)


def set_assignees(task_id, user_ids):
    body = json.dumps({"assignees": [{"id": uid} for uid in user_ids]}).encode()
    return http_json(f"{VIKUNJA_BASE}/tasks/{task_id}/assignees/bulk", method="POST", data=body)


def main():
    if not VIKUNJA_TOKEN:
        sys.exit("Set VIKUNJA_TOKEN")

    log("=== step 1: sharing projects with the users who need access ===")
    share_failures = []
    for project_id, usernames in NEEDED_SHARES.items():
        for username in usernames:
            try:
                share_project_with_user(project_id, username)
                log(f"shared project {project_id} with {username}")
            except urllib.error.HTTPError as e:
                body = e.read().decode()
                if '"code":7004' in body or "already" in body.lower():
                    log(f"project {project_id} + {username}: already shared, skipping")
                else:
                    log(f"FAILED to share project {project_id} with {username}: {e} {body}")
                    share_failures.append((project_id, username))

    log(f"\n=== step 2: backfilling assignees on reimported tasks ===")
    with open(CLICKUP_DUMP) as f:
        clickup_tasks = {t["id"]: t for t in json.load(f)}
    ledger = json.load(open(LEDGER_PATH))

    fixed, still_failed, no_assignees_needed = 0, 0, 0
    for clickup_id, vikunja_task_id in ledger.items():
        task = clickup_tasks.get(clickup_id)
        if not task:
            continue
        assignee_ids = []
        for a in task.get("assignees", []):
            email = a["email"]
            if email in EXCLUDED_EMAILS:
                continue
            uid = EMAIL_TO_VIKUNJA_ID.get(email)
            if uid and uid not in assignee_ids:
                assignee_ids.append(uid)

        if not assignee_ids:
            no_assignees_needed += 1
            continue

        try:
            set_assignees(vikunja_task_id, assignee_ids)
            log(f"[clickup {clickup_id}] vikunja task {vikunja_task_id}: assignees set to {assignee_ids}")
            fixed += 1
            time.sleep(0.15)
        except Exception as e:
            log(f"[clickup {clickup_id}] vikunja task {vikunja_task_id}: STILL FAILED: {e}")
            still_failed += 1

    log(
        f"\n=== done: {len(NEEDED_SHARES)} projects processed for sharing ({len(share_failures)} share failures), "
        f"{fixed} tasks got assignees set, {still_failed} still failing, "
        f"{no_assignees_needed} tasks needed no assignee ==="
    )


if __name__ == "__main__":
    main()
