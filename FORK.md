# DocSales Fork Notes

This is `docsales/vikunja`, a fork of `go-vikunja/vikunja` deployed at tasks.docsales.com via Railway. `AGENTS.md` (symlinked as `CLAUDE.md`) is upstream's own file — fork-specific policy lives here instead, so upstream syncs and any future upstream-bound PR never need to touch it.

## Two categories of change

1. **Fork-only** — exists only because this is a fork; has no value upstream (or would be actively wrong there). Example: the `github.repository == 'go-vikunja/vikunja'` guards in `.github/workflows/*.yml` that skip jobs depending on secrets/config this fork doesn't have (Release job's S3/Docker Hub publish, Crowdin sync, auto-labeling, nixpkgs update, issue-closed-comment bot). Commit these directly to this fork's `main`, never send them upstream.

2. **Upstream-able** — a generic bug fix, security fix, or feature that isn't DocSales-specific and would benefit the original project. Examples: the echo v5.3.0 routing panic fix, the CodeQL-flagged sql-injection/path-injection/allocation-size fixes, the Actions least-privilege permissions hardening. These land on this fork's `main` too (so the deploy isn't blocked waiting on an upstream release), but are also candidates for a separate PR to `go-vikunja/vikunja` — ask before opening one, since it's a PR to a repo we don't control.

## Customization strategy: config over forking components

When DocSales needs something branded or customized (app name, login screen image, colors, SMTP, etc.), prefer extending Vikunja's own configuration system over hardcoding it into a fork-only component edit:

- Vikunja already does this for some things — e.g. `VIKUNJA_SERVICE_CUSTOMLOGOURL` / `VIKUNJA_SERVICE_CUSTOMLOGOURLDARK`, and the whole `VIKUNJA_MAILER_*` SMTP block. Check `pkg/config/config.go` and `config.yml.sample` for what already exists before writing new fork-only code.
- If the option doesn't exist yet (a custom app name string, a custom login background image), the better fix is to add it as a real, generic Vikunja config option — not to hardcode "DocSales Tasks Management" into a component. The generic plumbing is upstream-able; the actual DocSales-flavored values (logo URL, name string, brand colors) live only in this fork's Railway environment variables / `config.yml`, never in committed code.
- This keeps future upstream merges low-conflict (upstream doesn't touch config keys we added, and if it does it's an additive conflict, not a "whose branding wins" conflict) and makes the customization portable — changing a brand value later is an env var change, not a redeploy-from-source.

## Merging from upstream

Merge, don't reset/overwrite. `git merge upstream/main` (or a PR from `go-vikunja/vikunja`'s `main` into this fork's `main`) preserves both histories; conflicts, if upstream touches a file this fork has patched, need manual resolution — nothing is silently lost.
