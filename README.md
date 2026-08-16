# Open Review Assistant

A privacy-first adaptive review engine for learners and coding agents. It keeps
prompts, answers, schedules, and review history in a local SQLite database and
exposes the same small workflow through a command-line interface and an MCP
server.

This repository is a clean public core extracted from a larger personal study
system. It contains no real learner records, exam questions, private notes, or
production databases. The demo content is synthetic.

## Why this project exists

Many review tools combine content, scheduling, and user data in a hosted
service. Open Review Assistant keeps the durable state on your machine, uses a
deterministic scheduling policy, and makes every schedule transition auditable.
An agent can select a due item, present it without exposing the stored answer,
then record a score after the learner responds.

## Features

- Local SQLite storage with foreign keys and integrity checks.
- Deterministic due-item selection and spaced-review scheduling.
- Answer-safe retrieval: `next` omits the stored answer by default.
- Immutable review events recording previous and next intervals.
- JSON output for scripts and agents.
- Dependency-free Python core.
- MCP tools over standard input/output.
- Synthetic demo data and unit tests.

## Quick start

Python 3.10 or newer is required.

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -e .

open-review --database review.sqlite3 init
open-review --database review.sqlite3 seed-demo
open-review --database review.sqlite3 next
```

After answering the returned prompt, grade the item from `0` to `5`:

```bash
open-review --database review.sqlite3 grade ITEM_ID 4
open-review --database review.sqlite3 stats
```

All commands support `--json`. The database path is explicit so a test database
cannot silently replace a real one.

## CLI

```text
open-review init
open-review add --title TITLE --prompt PROMPT --answer ANSWER [--tags TAG ...]
open-review next [--tag TAG] [--show-answer]
open-review grade ITEM_ID SCORE
open-review stats
open-review seed-demo
```

Scores follow a compact, transparent scale:

| Score | Meaning | Scheduling effect |
| --- | --- | --- |
| 0 | No recall | Restart tomorrow |
| 1 | Incorrect | Restart tomorrow |
| 2 | Hard | Shorten the current interval |
| 3 | Correct with effort | Grow the interval conservatively |
| 4 | Correct | Grow using the current ease factor |
| 5 | Easy | Grow faster and raise the ease factor |

## MCP server

Run the stdio server with:

```bash
open-review-mcp --database /absolute/path/to/review.sqlite3
```

It exposes four tools:

- `review_add_item`
- `review_next`
- `review_grade`
- `review_stats`

Example Codex configuration:

```toml
[mcp_servers.open_review]
command = "open-review-mcp"
args = ["--database", "/absolute/path/to/review.sqlite3"]
```

The server implements the MCP initialization, tool-listing, and tool-call
subset needed for this workflow. Transport is newline-delimited JSON-RPC over
stdio, and logs are never written to stdout.

## Privacy model

- No network calls, telemetry, accounts, or cloud synchronization.
- Database files and journals are ignored by Git.
- Answers are not returned by `next` unless explicitly requested.
- The public repository uses only synthetic examples.

Local-first is not the same as encrypted. Protect the device and database file
according to the sensitivity of your material. See [SECURITY.md](SECURITY.md).

## Roadmap

This public core is extracted from a larger system that is used and improved
continuously. Planned public milestones include:

- Provider-agnostic AI generation of question variants that test the same
  knowledge from different angles without copying private source material.
- Source-linked web and semantic review to check generated items for factual
  correctness, knowledge coverage, ambiguity, and unintended answer leakage.
- Reproducible evaluation fixtures for variant quality, prompt injection, and
  answer-safety regressions.
- Expanded MCP tools for orchestrating generation, verification, review, and
  weak-point analysis while keeping durable learner data local.

These capabilities will be added behind explicit interfaces so the scheduling
core remains inspectable, offline-capable, and independent of any single model
provider.

## Development

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

Contributions are welcome. Please read [CONTRIBUTING.md](CONTRIBUTING.md).
