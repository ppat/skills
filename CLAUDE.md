# CLAUDE.md

Agent Skills published two ways from one tree: the `skills` CLI (any agent) and a Claude Code plugin marketplace.
Nothing here runs on its own. Every skill is consumed on someone else's machine, so a change here changes how
their agent behaves.

## Layout

| Path | Role |
| --- | --- |
| `skills/<name>/SKILL.md` | The skill. The folder is the unit consumers receive |
| `.claude-plugin/marketplace.json` | Marketplace `ppatlabs` with one bundle plugin `ppatlabs` (`source: "./"`, `strict: false`) that lists every skill folder |
| `scripts/` | The skills-specific checks, run through `mise.toml` tasks |
| `release-please-config.json`, `.release-please-manifest.json` | One repository-wide version, `vX.Y.Z` tags |

## Invariants

**A skill folder ships wholesale.** `skills add` copies the whole folder, skipping only `metadata.json`, `.git` and
`__pycache__`. Put nothing in `skills/<name>/` that a consumer should not receive: evals, fixtures, READMEs and
changelogs live outside it. Links from a `SKILL.md` must resolve inside its own folder, because nothing outside
it is installed.

**The folder name is public API.** It equals the frontmatter `name`. Consumers select a skill by that name
(`--skill <name>`), invoke it with it (`/ppatlabs:<name>`), and the `skills` CLI names the installed folder
after it. Renaming a skill is a breaking change (`!`).

**Frontmatter stays inside the Agent Skills spec fields** (`name`, `description`, `license`, `compatibility`,
`metadata`, `allowed-tools`). Claude Code accepts more, but claude.ai uploads, the Skills API and the spec's
reference validator reject unknown fields.

**The marketplace lists exactly the skill folders on disk.** Adding or removing a skill means editing the
plugin's `skills` array in the same commit. `claude plugin validate` does not notice an unlisted folder, so
`scripts/check_marketplace.py` enforces this.

**The version lives in one place that Claude Code reads:** the plugin entry's `version` in `marketplace.json`.
release-please bumps it through `extra-files` (jsonpath selects the entry by name), in step with
`.release-please-manifest.json`, and the checks fail if the two disagree. Hand-edit neither. Never add a
`plugin.json`: Claude Code prefers its `version` over the marketplace entry's without any warning.

| Consumer | What an update is |
| --- | --- |
| Claude Code plugin | A change of the entry's `version`, so users see changes only after a release |
| `skills` CLI | A change of the skill folder's content at the ref they installed from (the default branch unless pinned to a tag). It ignores `version` |

**Spec exceptions are named, narrow and self-expiring.** `ALLOWED_ERRORS` in `scripts/lint_skills_spec.py` accepts
one skillscheck error per entry, for one skill and one check id. An entry that stops matching fails the lint, so
remove it when the fix lands. The current entry covers `derive-commit-taxonomy`'s description: 1,270 characters,
over the spec's 1,024-character limit but within Claude Code's 1,536. Trimming it closes the exception.

## Checks

`mise run lint` runs the skills-specific checks locally and in the `skills` job of `.github/workflows/lint.yaml`.
The tools come from `mise.toml`. Commit messages, markdown, YAML, workflow security and the generic pre-commit
hooks run through the shared `ppat/github-workflows` jobs in the same workflow. Run `pre-commit run --all-files`
locally for most of those.

| Task | Catches | Does not catch |
| --- | --- | --- |
| `lint:manifest`: `claude plugin validate . --strict` | Marketplace schema, reserved names, path traversal | Anything inside a `SKILL.md`: it passes a bad name, name/folder mismatch, unknown fields and broken links |
| `lint:spec`: skillscheck on `skills/` | Spec fields and lengths, name matching folder, unknown frontmatter fields, broken links, secrets | A `SKILL.md` link that leaves its folder but resolves in this repository; manifest state |
| `lint:sync`: `scripts/check_marketplace.py` | Marketplace list vs folders, version drift from release-please, a stray `plugin.json` | Skill content |
| `lint:install`: `scripts/check_install.py` | What the `skills` CLI actually installs, compared file by file with `skills/` | Claude Code loading |

skillscheck rates unknown fields and broken links below error; `PROMOTED_TO_ERROR` in the script makes them fail. Other
warnings (body over 500 lines or 5,000 tokens) are printed but do not fail. Checks need no credentials, and every
lint job runs on fork pull requests: checkouts use the pull request's head SHA because a fork's branch name does
not exist here.

## Gotchas

- skillscheck pointed at the repository root runs its Claude adapter, which requires a `plugin.json`. Run it on
  `skills/`. The manifest is `claude plugin validate`'s job.
- skillscheck checks that links in `references/` files stay inside the skill folder, but not links in `SKILL.md`
  itself. `../../README.md` passes every check here and is broken once installed.
- `claude plugin eval <path>` does not resolve this layout as a plugin. It reports "Plugin under test: none
  resolved" and runs cases against plain Claude Code. Behavioural evals would have to target the installed
  `ppatlabs@ppatlabs` and cost model spend, so the repository has none yet.
- `python` is pinned in `mise.toml` for the scripts. The pin also matters to mise's `pipx:` backend: when mise's
  shims are on `PATH` and no `python` is configured, installing skillscheck fails with "No version is set for
  shim: python".
- `mise.lock` (format v2) and the `.mise/locks/` files it references are committed; `mise install --locked` in the
  `skills` job fails if either is stale. The `setup-repository-tools` default mise cannot read format v2, so the
  job pins `mise_version`. `[settings.npm] package_manager = "aube"` in `mise.toml` makes `mise lock` embed the
  `npm:` dependency graph the locked install needs; a global `bun` package manager silently omits it.
- release-please reads its config from `main` through the API, never from the pull request branch, so its dry run
  cannot validate config changes that have not landed.

## Commit conventions

commitlint gates every pull request, and release-please derives the version and changelog from commit headers.

- Scopes: `''`, `github-actions`, `internal-dependencies` and `release`, plus every skill folder name, which
  `commitlint.config.js` reads from `skills/`. Scope a change to one skill with its folder name. Scope a change
  that spans skills, or removes one, with `''`.
- There is no `bump-minor-pre-major`, so `!` cuts a major release even before `1.0.0`.
- Do not hand-edit `CHANGELOG.md`, `.release-please-manifest.json` or the plugin `version`.
