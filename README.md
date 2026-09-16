# skills

[Agent Skills](https://agentskills.io) for coding agents. Each skill teaches a method, not an answer: it gives the
agent an ordered way to work through a kind of decision, plus the traps that are easy to miss.

## Catalog

| Skill | Use it when |
| --- | --- |
| [`derive-commit-taxonomy`](skills/derive-commit-taxonomy/SKILL.md) | Designing, overhauling or auditing a repository's conventional-commit types and scopes, and the commitlint, release-please and Renovate setup that enforces them |
| [`select-framework-or-tool`](skills/select-framework-or-tool/SKILL.md) | Choosing between real alternatives (a language, framework, library, database, toolchain, platform) in a way you can defend later |

## Install

### Any agent: the `skills` CLI

[`skills`](https://www.npmjs.com/package/skills) installs into Claude Code, Codex, Cursor and other agents.

```bash
# List the skills in this repository
npx skills add ppat/skills --list

# Install one skill into the current project (prompts for which agents)
npx skills add ppat/skills --skill derive-commit-taxonomy

# Install every skill for your user, for specific agents, without prompts
npx skills add ppat/skills --skill '*' --agent claude-code codex --global --yes

# Pull in later changes
npx skills update
```

To pin a release, add its tag to the source, for example `npx skills add ppat/skills#v1.2.3 --skill select-framework-or-tool`.
Releases are listed on the [releases page](https://github.com/ppat/skills/releases).

### Claude Code: plugin marketplace

All skills ship together as one plugin, `ppatlabs`. In a Claude Code session:

```text
/plugin marketplace add ppat/skills
/plugin install ppatlabs@ppatlabs
```

Or from a shell:

```bash
claude plugin marketplace add ppat/skills
claude plugin install ppatlabs@ppatlabs
```

Claude uses a skill on its own when your request matches its description. To invoke one directly, run
`/ppatlabs:<skill-name>`, for example `/ppatlabs:select-framework-or-tool`. The plugin updates when a new release
is published.

Use one install method per agent. Installing the same skill both ways gives Claude Code two copies.

## Contributing

[CLAUDE.md](CLAUDE.md) covers the repository's invariants and how to check a change locally (`mise run lint`).

## License

[MIT](LICENSE)
