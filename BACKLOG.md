# Backlog

Non-obvious open threads, kept intentionally light on detail since this repo is public. Ask Mauricio for specifics/the full report where noted.

## Ideas (not started)

- [ ] **Custom Fields** - deprioritized 2026-07-20, tracked here per Mauricio's request to keep adding ideas rather than dropping them. A real cadastro (definitions table + per-task values table), not hardcoded columns - hardcoding forces a code change per new field. Before building: [go-vikunja/vikunja#120](https://github.com/go-vikunja/vikunja/issues/120) has been open since 2022 with real community demand and zero maintainer response in 4 years - propose a design there first rather than showing up with a finished PR.

## Completed 2026-07-19/20/21

- PR #12 - fix per-page titles reverting to Vikunja branding
- PR #13 - exclude brand icons from the 1-year immutable cache
- PR #14 - fork-specific user management routes (list/create/status/delete)
- PR #15 - `/users` frontend page for the above
- PR #16 - sync 36 commits from upstream (brings several official GHSA security fixes)
- PR #17/#18 - 4 mechanical fixes for HIGH-impact `/16-eyes audit` findings (landed on `main` via #18 after #17 merged into an intermediate branch by mistake)
- [go-vikunja/vikunja#3247](https://github.com/go-vikunja/vikunja/pull/3247) - the same 4 fixes, upstreamed
- Full `/16-eyes audit` run: 23 lenses, 73 candidates → 66 confirmed real findings, 31 classified safe (mechanical) / 23 risky (needs a decision)
- Instance-admin bootstrap gap - resolved via a direct DB write on Mauricio's own account
- PR #20 - lands the `/users` admin page on `main` (previous attempt, #15, had merged into an intermediate branch by mistake - same class of bug as #17)
- PR #21 - fix admin create-user form rejecting every request (empty `language` field failed a validator that was never meant to require one)
- PR #22 - fix the same form actually rejecting the far more common case: any dotted `firstname.lastname` username, because `govalidator.IsURL` treats `word.word` as URL-like
- **Full ClickUp reimport (2026-07-20/21)**: the original import (~316 tasks) had silently dropped 102 open tasks (concentrated in 2 ClickUp lists, one 100% missed) and never set any assignee. Wiped all tasks and reimported all 418 currently-open tasks with correct project placement, assignees, ClickUp tags as labels, subtask/parent relations, and attachments. Along the way: fixed most projects having no team/user sharing configured (assignment was silently 403ing for every non-owner user), fixed a Cloudflare edge cache serving a stale pre-rebrand favicon and a separate Cloudflare bot-challenge blocking attachment uploads (both needed a change in the Cloudflare dashboard, not this repo), and recovered from a self-inflicted bug where a title-only task update wiped every other field (`pkg/models/tasks.go`'s `updateSingleTask` treats a partial body as authoritative for every column it lists, including assignees) - recomputed and restored description/priority/due_date/assignees for all 418 tasks from the original ClickUp data.
- Gustavo Arnaldo and Rafael Correia: both got real accounts via Google SSO; their ClickUp-sourced tasks were reassigned from their placeholders (Gustavo's 65 solo tasks were on Mauricio; Rafael's 10 co-assigned tasks had him excluded per instruction, then added back once his account existed) without disturbing co-assignees' own legitimate assignments on the same tasks.
- PR #23 - dark mode rendering task titles and team names in the vivid brand pink instead of neutral text color, in the two views where that RouterLink-color override had never been added
- PR #24 - new ClickUp migration module for the `/migrate` menu (gated behind `VIKUNJA_MIGRATION_CLICKUP_ENABLE`, off by default) - reused for the reimport's attachment step too
- [go-vikunja/vikunja#3255](https://github.com/go-vikunja/vikunja/pull/3255) - the ClickUp migration module, upstreamed (a clean subset of PR #24 - none of this fork's branding/admin-panel changes)

## Security follow-ups (from the 2026-07-19 `/16-eyes audit`)

23 findings need a human product/security decision before fixing (vs. 31 mechanical ones, already handled). Of the 11 rated high-impact, 6 are resolved (2 by the upstream sync landing GHSA fixes for the same bugs, 4 by [go-vikunja/vikunja#3247](https://github.com/go-vikunja/vikunja/pull/3247)/PR #18 on this fork). **5 remain open**, title only (ask for the full report for specifics):

- [ ] Local-login config flag doesn't fully cover one login path — needs a decision on an account-type exception
- [ ] Disabling the 2FA feature flag still bypasses 2FA for already-enrolled users (now logged - see [go-vikunja/vikunja#3247](https://github.com/go-vikunja/vikunja/pull/3247) - but the underlying behavior is unchanged)
- [ ] OAuth authorize endpoint has no client registry or consent screen - full fix is a client-registration table + consent UI; a smaller interim hardening is available if wanted sooner
- [ ] OAuth-issued tokens are unscoped (same privilege as a full login) - needs a scope taxonomy design, touches the `veans` bot's own flow
- [ ] Outbound-proxy config can silently weaken the SSRF guard - full fix is a product decision; a warning now logs the risk

