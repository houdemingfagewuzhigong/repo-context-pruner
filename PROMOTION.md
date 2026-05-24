# Launch Promotion

Repository: https://github.com/houdemingfagewuzhigong/repo-context-pruner

## Hacker News

Title:

Show HN: Repo Context Pruner - build safer context packs for AI coding agents

Body:

I built a zero-dependency Python CLI for a problem I keep hitting with AI coding agents: giving them enough repo context without dumping the whole project or accidentally including secrets.

Repo Context Pruner scores source files, README/project metadata, tests, and workflows, then writes a size-bounded `context-pack.md`. It also redacts token-like values and emits `context-manifest.json` plus SARIF warnings for redactions.

Repo: https://github.com/houdemingfagewuzhigong/repo-context-pruner

## Reddit r/opensource

I built Repo Context Pruner, a small zero-dependency CLI that creates safe context packs for AI coding agents.

It scores repo files, includes the most useful source/docs/tests/workflows under a byte budget, redacts token-like values, and emits JSON/SARIF so teams can audit what was sent to an agent.

Repo: https://github.com/houdemingfagewuzhigong/repo-context-pruner

Feedback wanted: what signals should a context-pruning tool use to decide what an agent should see?

## Reddit r/selfhosted

If you self-host coding-agent workflows or run local MCP tools, I made Repo Context Pruner: a zero-dependency CLI that builds a safe, size-bounded `context-pack.md` before handing a repo to an AI agent.

It redacts token-like values and writes a JSON manifest/SARIF output so you can audit the context bundle.

Repo: https://github.com/houdemingfagewuzhigong/repo-context-pruner

## Reddit r/programming

Context engineering for coding agents is still messy. I built Repo Context Pruner to score a repository, pick the highest-signal files under a byte budget, redact secret-like values, and emit Markdown/JSON/SARIF outputs.

Zero dependencies, one Python file.

Repo: https://github.com/houdemingfagewuzhigong/repo-context-pruner

## X Short Post

Built Repo Context Pruner: create safe, size-bounded context packs before handing a repo to an AI coding agent.

Scores files, redacts token-like values, outputs Markdown + JSON + SARIF.

https://github.com/houdemingfagewuzhigong/repo-context-pruner

## X Long Post

AI coding agents do better with focused repo context, but pasting everything is noisy and risky.

I built Repo Context Pruner: a zero-dependency Python CLI that scores repo files, builds a byte-bounded `context-pack.md`, redacts token-like values, and emits JSON/SARIF so you can audit exactly what went into the agent context.

Repo: https://github.com/houdemingfagewuzhigong/repo-context-pruner
