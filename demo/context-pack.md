# Repo Context Pack

- source: `repo-context-pruner`
- files considered: 6
- files included: 6
- byte budget: 50000
- manifest digest: `349db3e414d0`


## README.md

```
# Repo Context Pruner

Build a small, safe context pack before you hand a repository to an AI coding agent.

Repo Context Pruner is a zero-dependency Python CLI that scores source files, redacts secret-like values, and emits a size-bounded `context-pack.md` plus JSON/SARIF metadata. It is built for developers who want better context engineering without pasting an entire repo into an agent.

## Demo

![Repo Context Pruner demo](demo/demo.svg)

## Quick Start

```bash
python3 repo_context_pruner.py . --max-bytes 80000 --sarif context.sarif
```

Outputs:

- `context-pack.md`: curated Markdown bundle for an AI agent
- `context-manifest.json`: file scores, inclusion decisions, redaction counts
- `context.sarif`: warning results for redacted secret-like values

## Why It Helps

AI coding agents work better when they get focused context instead of repo dumps. This tool prioritizes files that usually matter most:

- README and project metadata
- source code
- tests
- CI/workflow files
- compact files that fit in a context budget

It penalizes low-signal files and redacts token-like values before the pack is written.

## GitHub Actions

```yaml
name: Context Pack

on:
  pull_request:

jobs:
  context:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Build agent context pack
        run: python3 repo_context_pruner.py . --max-bytes 80000 --sarif context.sarif
```

## JSON And SARIF

```bash
python3 repo_context_pruner.py . --manifest context-manifest.json --sarif context.sarif
```

The JSON manifest makes it easy to inspect why each file was included or skipped. SARIF lets security-aware teams surface redaction warnings in code scanning workflows.

## License

MIT
```


## tests/test_repo_context_pruner.py

```
import json
import tempfile
import unittest
from pathlib import Path

import repo_context_pruner as pruner


class RepoContextPrunerTests(unittest.TestCase):
    def test_redacts_and_scores_context(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "README.md").write_text("# Demo\n")
            token = "github_pat_" + "A" * 40
            (root / "app.py").write_text(f"API_TOKEN={token}\nprint('ok')\n")

            scores, pack = pruner.collect(root, 10_000, [])

        by_path = {item.path: item for item in scores}
        self.assertIn("README.md", by_path)
        self.assertIn("README.md", pack)
        self.assertEqual(by_path["app.py"].redactions, 1)

    def test_sarif_serializes(self):
        score = pruner.FileScore("app.py", 1, 10, ["source code"], 2, True)
        data = pruner.sarif([score])
        self.assertEqual(data["version"], "2.1.0")
        self.assertEqual(len(data["runs"][0]["results"]), 1)
        json.dumps(data)


if __name__ == "__main__":
    unittest.main()
```


## repo_context_pruner.py

```
#!/usr/bin/env python3
"""Build a small, safe context pack for AI coding agents."""

from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
import os
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path


IGNORE_DIRS = {
    ".git",
    ".hg",
    ".svn",
    ".venv",
    "venv",
    "node_modules",
    "dist",
    "build",
    "__pycache__",
    ".pytest_cache",
}

TEXT_EXTENSIONS = {
    "",
    ".css",
    ".go",
    ".html",
    ".java",
    ".js",
    ".jsx",
    ".json",
    ".md",
    ".mjs",
    ".py",
    ".rb",
    ".rs",
    ".sh",
    ".sql",
    ".swift",
    ".toml",
    ".ts",
    ".tsx",
    ".txt",
    ".yaml",
    ".yml",
}

SECRET_PATTERNS = [
    re.compile(r"github_pat_[A-Za-z0-9_]{30,}"),
    re.compile(r"ghp_[A-Za-z0-9]{30,}"),
    re.compile(r"sk-[A-Za-z0-9_-]{20,}"),
    re.compile(r"(?i)\b(api[_-]?key|token|secret|password)\b\s*[:=]\s*['\"]?[^'\"\s]{12,}"),
]


@dataclass
class FileScore:
    path: str
    score: int
    bytes: int
    reason: list[str]
    redactions: int
    included: bool


def is_text(path: Path) -> bool:
    if path.suffix.lower() not in TEXT_EXTENSIONS and path.name not in {".env", ".gitignore"}:
        return False
    try:
        return b"\0" not in path.read_bytes()[:2048]
    except OSError:
        return False


def iter_files(root: Path):
    for current_root, dirnames, filenames in os.walk(root):
        dirnames[:] = [name for name in dirnames if name not in IGNORE_DIRS]
        for filename in filenames:
            path = Path(current_root) / filename
            if is_text(path):
                yield path


def redact(text: str) -> tuple[str, int]:
    count = 0

    def repl(match: re.Match[str]) -> str:
        nonlocal count
        count += 1
        return "[REDACTED]"

    for pattern in SECRET_PATTERNS:
        text = pattern.sub(repl, text)
    return text, count


def score_file(rel: str, text: str, redactions: int) -> tuple[int, list[str]]:
    score = 0
    reason: list[str] = []
    name = Path(rel).name.lower()
    suffix = Path(rel).suffix.lower()
    lower = rel.lower()

    if name in {"readme.md", "package.json", "pyproject.toml", "cargo.toml", "go.mod"}:
        score += 40
        reason.append("project identity")
    if suffix in {".py", ".ts", ".tsx", ".js", ".go", ".rs", ".swift"}:
        score += 20
        reason.append("source code")
    if "test" in lower or "spec" in lower:
        score += 12
        reason.append("tests")
    if lower.startswith(".github/workflows/"):
        score += 10
        reason.append("automation")
    if len(text) < 12_000:
        score += 8
        reason.append("compact")
    if redactions:
        score -= 30
        reason.append("redacted secrets")
    if "lock" in name or suffix in {".png", ".jpg", ".jpeg", ".gif", ".svg"}:
        score -= 20
        reason.append("low context value")

    return score, reason


def collect(root: Path, max_bytes: int, include_globs: list[str]) -> tuple[list[FileScore], str]:
    candidates: list[tuple[FileScore, str]] = []
    for path in iter_files(root):
        rel = str(path.relative_to(root))
        if include_globs and not any(fnmatch.fnmatch(rel, pat) for pat in include_globs):
            continue
        raw = path.read_text(encoding="utf-8", errors="replace")
        clean, redactions = redact(raw)
        score, reason = score_file(rel, clean, redactions)
        candidates.append(
            (FileScore(rel, score, len(clean.encode()), reason, redactions, False), clean)
        )

    candidates.sort(key=lambda pair: (-pair[0].score, pair[0].bytes, pair[0].path))
    used = 0
    sections: list[str] = []
    scores: list[FileScore] = []
    for item, clean in candidates:
        block = f"\n\n## {item.path}\n\n```\n{clean.rstrip()}\n```\n"
        size = len(block.encode())
        if used + size <= max_bytes and item.score > 0:
            item.included = True
            used += size
            sections.append(block)
        scores.append(item)

    digest = hashlib.sha256("\n".join(item.path for item in scores).encode()).hexdigest()[:12]
    header = (
        "# Repo Context Pack\n\n"
        f"- source: `{root.name}`\n"
        f"- files considered: {len(scores)}\n"
        f"- files included: {sum(1 for item in scores if item.included)}\n"
        f"- byte budget: {max_bytes}\n"
        f"- manifest digest: `{digest}`\n"
    )
    return scores, header + "".join(sections) + "\n"


def sarif(scores: list[FileScore]) -> dict:
    results = []
    for item in scores:
        if item.redactions:
            results.append(
                {
                    "ruleId": "repo-context-pruner.redacted-secret",
                    "level": "warning",
                    "message": {"text": f"{item.redactions} secret-like value(s) redacted from context pack"},
                    "locations": [
                        {"physicalLocation": {"artifactLocation": {"uri": item.path}}}
                    ],
                }
            )
    return {
        "version": "2.1.0",
        "$schema": "https://json.schemastore.org/sarif-2.1.0.json",
        "runs": [{"tool": {"driver": {"name": "Repo Context Pruner", "rules": []}}, "results": results}],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build a safe, size-bounded context pack for AI agents.")
    parser.add_argument("path", nargs="?", default=".", help="repository path")
    parser.add_argument("--max-bytes", type=int, default=80_000, help="context pack byte budget")
    parser.add_argument("--output", default="context-pack.md", help="markdown output path")
    parser.add_argument("--manifest", default="context-manifest.json", help="JSON manifest output path")
    parser.add_argument("--sarif", default=None, help="optional SARIF output path")
    parser.add_argument("--include", action="append", default=[], help="glob to include; can be repeated")
    args = parser.parse_args(argv)

    root = Path(args.path).resolve()
    if not root.exists():
        print(f"Path does not exist: {root}", file=sys.stderr)
        return 2

    scores, pack = collect(root, args.max_bytes, args.include)
    Path(args.output).write_text(pack)
    Path(args.manifest).write_text(json.dumps([asdict(item) for item in scores], indent=2) + "\n")
    if args.sarif:
        Path(args.sarif).write_text(json.dumps(sarif(scores), indent=2) + "\n")

    included = sum(1 for item in scores if item.included)
    redactions = sum(item.redactions for item in scores)
    print(f"wrote {args.output}: {included}/{len(scores)} files included, {redactions} redactions")
    return 1 if redactions else 0


if __name__ == "__main__":
    raise SystemExit(main())
```


## .github/workflows/ci.yml

```
name: CI

on:
  pull_request:
  push:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Run tests
        run: python3 -m unittest discover -s tests -q
      - name: Build demo context pack
        run: python3 repo_context_pruner.py . --max-bytes 50000 --sarif context.sarif || true
```


## .gitignore

```
.env
.env.*
*.token
github_token
secrets/
.config/
__pycache__/
*.pyc
.pytest_cache/
.DS_Store
context-pack.md
context-manifest.json
context.sarif
```


## LICENSE

```
MIT License

Copyright (c) 2026 houdemingfagewuzhigong

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

