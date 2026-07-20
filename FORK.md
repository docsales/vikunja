# DocSales Fork Notes

This is `docsales/vikunja`, a fork of `go-vikunja/vikunja` deployed at tasks.docsales.com via Railway. `AGENTS.md` (symlinked as `CLAUDE.md`) is upstream's own file — fork-specific policy lives here instead, so upstream syncs and any future upstream-bound PR never need to touch it.

## Two categories of change

1. **Fork-only** — exists only because this is a fork; has no value upstream (or would be actively wrong there). Example: the `github.repository == 'go-vikunja/vikunja'` guards in `.github/workflows/*.yml` that skip jobs depending on secrets/config this fork doesn't have (Release job's S3/Docker Hub publish, Crowdin sync, auto-labeling, nixpkgs update, issue-closed-comment bot). Commit these directly to this fork's `main`, never send them upstream.

   Another example: `pkg/routes/api/v1/docsalesadmin` and the `/users` frontend page. This instance has no Vikunja Pro license, so `/admin/*` (`license.FeatureAdminPanel`) 404s even for an instance admin — `pkg/license/license.go` has an explicit note asking that removing/bypassing that gate only happen with the requester's informed sign-off, since it funds Vikunja's development. Rather than touch it, `/api/v1/docsales-admin` reuses the exact same handlers/model functions under a separate route group gated only by `RequireInstanceAdmin()` (a plain `is_admin` check, not a license check). Follow this pattern for any future admin-panel-adjacent feature; never touch `RequireFeature(license.FeatureAdminPanel)` or `isInstanceAdmin` in `pkg/models/admin_bypass.go` without revisiting the license-purchase question with whoever owns that decision first.

   One real gap this created: nothing in Vikunja (API or CLI) can set `is_admin` on any user without an active license (`vikunja user set-admin` carries the identical gate) — so bootstrapping the *first* instance admin on an unlicensed fork has no built-in path. See `BACKLOG.md`.

2. **Upstream-able** — a generic bug fix, security fix, or feature that isn't DocSales-specific and would benefit the original project. Examples: the echo v5.3.0 routing panic fix, the CodeQL-flagged sql-injection/path-injection/allocation-size fixes, the Actions least-privilege permissions hardening. These land on this fork's `main` too (so the deploy isn't blocked waiting on an upstream release), but are also candidates for a separate PR to `go-vikunja/vikunja` — ask before opening one, since it's a PR to a repo we don't control.

## Customization strategy: config over forking components

When DocSales needs something branded or customized (app name, login screen image, colors, SMTP, etc.), prefer extending Vikunja's own configuration system over hardcoding it into a fork-only component edit:

- Vikunja already does this for some things — e.g. `VIKUNJA_SERVICE_CUSTOMLOGOURL` / `VIKUNJA_SERVICE_CUSTOMLOGOURLDARK`, and the whole `VIKUNJA_MAILER_*` SMTP block. Check `pkg/config/config.go` and `config.yml.sample` for what already exists before writing new fork-only code.
- If the option doesn't exist yet (a custom app name string, a custom login background image), the better fix is to add it as a real, generic Vikunja config option — not to hardcode "DocSales Tasks Management" into a component. The generic plumbing is upstream-able; the actual DocSales-flavored values (logo URL, name string, brand colors) live only in this fork's Railway environment variables / `config.yml`, never in committed code.
- This keeps future upstream merges low-conflict (upstream doesn't touch config keys we added, and if it does it's an additive conflict, not a "whose branding wins" conflict) and makes the customization portable — changing a brand value later is an env var change, not a redeploy-from-source.

## Git workflow: always a PR

**Every change to this fork goes through a branch + pull request, merged into `main` — never a direct push to `main`, including infra fixes, CI/build breakage, and other "urgent" changes.** A broken deploy pipeline is not an exception: open the PR and merge it immediately rather than pushing straight to `main`. This applies regardless of who or what is making the change.

## Merging from upstream

Merge, don't reset/overwrite. `git merge upstream/main` (or a PR from `go-vikunja/vikunja`'s `main` into this fork's `main`) preserves both histories; conflicts, if upstream touches a file this fork has patched, need manual resolution — nothing is silently lost.

This repo uses **squash merge**. A PR's base branch only reaches `main` when *that* branch is separately merged into `main` — merging a PR into an intermediate branch (e.g. a fix PR based on a not-yet-merged sync branch) does not, by itself, land its commits on `main`, and because squash merge replaces the original commits with one new commit, `git log main..that-branch` will misleadingly list everything on the branch as "not yet on main" even after the content already landed via the squash commit. Check `git log --format="%H %P" <sha>` (one parent = squash) before assuming a merge chain worked; cherry-pick the specific squash commit onto fresh `main` to land it cleanly rather than re-merging the whole branch.

## Security audits (16-eyes)

`/16-eyes audit` reports are gitignored (`SECURITY_AUDIT_*.md`/`.json`, `.16-eyes/config.json`'s `output.gitignoreReports`) **on purpose**: this repo is public, and a full report includes exploit reproduction steps for findings that may not be fixed yet. Don't commit the raw report. `BACKLOG.md` tracks open findings at a title-only level (no reproduction detail); ask whoever ran the audit for the full report if you need it.
