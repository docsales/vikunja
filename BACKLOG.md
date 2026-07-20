# Backlog

Non-obvious open threads, kept intentionally light on detail since this repo is public. Ask Mauricio for specifics/the full report where noted.

## Completed 2026-07-19/20

- PR #12 - fix per-page titles reverting to Vikunja branding
- PR #13 - exclude brand icons from the 1-year immutable cache
- PR #14 - fork-specific user management routes (list/create/status/delete)
- PR #15 - `/users` frontend page for the above
- PR #16 - sync 36 commits from upstream (brings several official GHSA security fixes)
- PR #17/#18 - 4 mechanical fixes for HIGH-impact `/16-eyes audit` findings (landed on `main` via #18 after #17 merged into an intermediate branch by mistake)
- [go-vikunja/vikunja#3247](https://github.com/go-vikunja/vikunja/pull/3247) - the same 4 fixes, upstreamed
- Full `/16-eyes audit` run: 23 lenses, 73 candidates → 66 confirmed real findings, 31 classified safe (mechanical) / 23 risky (needs a decision)

## Security follow-ups (from the 2026-07-19 `/16-eyes audit`)

23 findings need a human product/security decision before fixing (vs. 31 mechanical ones, already handled). Of the 11 rated high-impact, 6 are resolved (2 by the upstream sync landing GHSA fixes for the same bugs, 4 by [go-vikunja/vikunja#3247](https://github.com/go-vikunja/vikunja/pull/3247)/PR #18 on this fork). **5 remain open**, title only (ask for the full report for specifics):

- [ ] Local-login config flag doesn't fully cover one login path — needs a decision on an account-type exception
- [ ] Disabling the 2FA feature flag still bypasses 2FA for already-enrolled users (now logged - see [go-vikunja/vikunja#3247](https://github.com/go-vikunja/vikunja/pull/3247) - but the underlying behavior is unchanged)
- [ ] OAuth authorize endpoint has no client registry or consent screen - full fix is a client-registration table + consent UI; a smaller interim hardening is available if wanted sooner
- [ ] OAuth-issued tokens are unscoped (same privilege as a full login) - needs a scope taxonomy design, touches the `veans` bot's own flow
- [ ] Outbound-proxy config can silently weaken the SSRF guard - full fix is a product decision; a warning now logs the risk

## Instance administration

- [ ] **No user can be flagged instance-admin on this deployment without a Vikunja Pro license** - both the API and the CLI refuse (see `FORK.md`). Needed to actually use `/docsales-admin` and `/users` (PR #14/#15). Options on the table, undecided as of 2026-07-20: a small fork-only "bootstrap first admin" addition, a manual one-off fix on the affected account, or purchasing the license (which also unlocks Time Tracking/Audit Logs/the real Admin Panel).
- [ ] Marcelo Medeiros: has two accounts (original local user/password + a new Google-OAuth one from his first SSO login, since email-fallback account linking is off by default). Needs his tasks migrated old to new (via the new `migrate-to` endpoint once an admin account is available) and adding to the DocSales and Financeiro teams. Blocked on the item above.

## Housekeeping

- [ ] PR #15 (`/users` admin page) was built and statically verified (typecheck, lint, translations) but never manually clicked through - reaching it requires an instance-admin account, which doesn't exist yet (see above). Worth a manual QA pass once one does.
