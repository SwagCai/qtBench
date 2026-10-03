# Inference scaffold

This directory runs one qtBench problem through a solver, the repository's
authoritative scored checker, and a fresh semantic judge for every candidate
that passes the checker. It is included in this repository. No research
trajectories, private candidate solutions, credentials, or provider outputs are included.

## Quick start

Use this from a clean Git checkout of qtBench on Linux or WSL2.
Clone the repository as described in the [main README](../README.md#quick-start).
The base qtBench environment, Git, `bubblewrap`, and the Codex CLI are required.
Install `bubblewrap` from the distribution package first. Both the UV host
interpreter and the system `/usr/bin/python3` or `/usr/local/bin/python3` used
inside the sandbox must be Python 3.11 or newer:

```bash
sudo apt update
sudo apt install bubblewrap
# Run from the qtBench repository root.
uv sync --locked
npm install --global @openai/codex@0.156.1
```

On Ubuntu 24.04, also load the packaged AppArmor profile if unprivileged user
namespaces are restricted:

```bash
sudo apt install apparmor-profiles apparmor-utils
sudo install -m 0644 \
  /usr/share/apparmor/extra-profiles/bwrap-userns-restrict \
  /etc/apparmor.d/bwrap-userns-restrict
sudo apparmor_parser -r /etc/apparmor.d/bwrap-userns-restrict
```

The [official Codex sandbox prerequisites](https://learn.chatgpt.com/docs/sandboxing#prerequisites)
cover other Linux distributions and troubleshooting.

First run the free preflight. It selects problem `5`, prepares only that
problem's public inputs, and proves that the local Codex sandbox allows work in
the solver workspace while denying an outside file and shell network sockets.
It neither needs an API key nor calls a model:

```bash
uv run --locked python inference/run.py 5 --check-only
```

Then export an OpenAI API key and start a short offline run:

```bash
export OPENAI_API_KEY='your-api-key'
uv run --locked python inference/run.py 5 --minutes 10 --offline
```

The problem argument may be a stable numeric ID or the exact registry name. The
default solver and judge model is `gpt-6-sol`; select another API-accessible
model with `--solver-model` and `--judge-model`. The default run is 120 total
wall-clock minutes, including semantic reviews and checker runs, and can incur
material API usage and cost. OpenAI API access is paid and subject to the
account's model access and rate limits, so begin with a short `--minutes` run.
Omit `--offline` to enable Codex hosted web search automatically for problems
2–30. Problem 1 always disables search. Model-generated shell commands never
receive network access.

A run stops successfully when one exact candidate receives a strict semantic
approval and passes the authoritative checker, or completes when its wall-clock
budget expires. Host evidence is written under
`~/.qtbench-inference/runs/<run-id>/`:

- `manifest.json` binds the problem, clean Git revision, models, prompt hashes,
  input manifest, limits, and Codex version;
- `submissions/<id>/` immutably captures every valid attempted source and its
  request before review;
- `judgements/<id>/` records the isolated judge packet, decision, checker
  receipt, and exact source hash;
- `solver/` contains segment prompts and Codex event logs; and
- `result.json` identifies the approved submission, source hash, and captured
  source path when the run succeeds.

Use `python inference/run.py --help` for the remaining timeout, model, state,
and Codex-binary options.

## Isolation and trust boundaries

The solver receives only the selected public problem statement, metadata,
targets, public combinatorial-object code, checker documentation, writable
scratch space, and `qtbench-submit`. It receives no checker implementation,
oracle, other problem, example solution, prior trajectory, Git history, host
credential, or user configuration. A clean checkout is required so the
recorded commit identifies the exact checker used.

Each submission is published atomically to a bounded file broker. The host
opens the broker directories before the solver starts and retains directory
file descriptors; host reads use `openat` with no-follow and nonblocking flags,
accept only bounded single-link regular files, and host responses are replaced
atomically relative to the retained descriptor. Replacing broker parents with
symlinks, FIFOs, links, or directories therefore cannot redirect a host read or
write. Transport parsing is bounded to one request per poll. A total absolute
run deadline covers solver, judge, checker, parsing, and feedback time.

Every valid request is captured before checking. Only a passing checker result
reaches the judge. The judge gets a new model context and private scratch
workspace containing only the trusted current problem context and the exact untrusted candidate packet. Malformed output,
provider failure, timeout, or uncertainty fails closed. Acceptance requires both
a checker pass and strict judge approval. The checker validates the
captured source hash, problem ID, evaluator kind, clean repository status, and
recorded commit. It never loads a generation oracle.

`OPENAI_API_KEY` remains in the host environment. The launcher passes it to
`codex login --with-api-key` on standard input, forces
`cli_auth_credentials_store="file"` in a private mode-0700 `CODEX_HOME`, strips
provider credentials from solver and judge tool environments, and removes the
authentication directory in `finally`. It does not put the key in arguments,
prompts, workspaces, or evidence.

The semantic judge is a review aid, not a proof of naturalness. Submitted prose
and source can attempt prompt injection, and a model can still make a wrong
semantic decision. Human mathematical review remains necessary. The solver can
also destroy its own workspace or flood its own bounded broker and thereby fail
a run; this does not grant access to the host checker or credentials.

The scaffold never falls back to an unsandboxed model process. This release
requires Linux, a mounted `/proc`, working `prctl` subreaper support, and a
working Codex permission profile; WSL2 is usable only when those same preflight
checks pass. Every solver, judge, and checker command runs under a dedicated
subreaper supervisor that kills and reaps descendants even if they change
session or process group. The preflight also requires Codex tools to run in a
private PID namespace, so sandboxed code cannot address host process IDs. macOS
is unsupported for this release: on macOS 14.2,
Codex CLI versions 0.155.0-alpha.9.2 and 0.156.1 fail the sandbox capability
probe with a `TIOCSTI` Seatbelt error, and macOS lacks the Linux containment
mechanism used here. Updating the CLI alone is not a verified workaround.

The isolation configuration follows the official Codex documentation for
[permission profiles](https://learn.chatgpt.com/docs/permissions),
[advanced configuration](https://learn.chatgpt.com/docs/config-file/config-advanced),
and [credential separation](https://developers.openai.com/api/docs/guides/agents-api/environments/security).

## Validation

Run the deterministic offline tests with:

```bash
uv run --extra dev --locked python -m pytest -q inference/tests
```

Platform-specific integration tests skip when unavailable. To exercise the
Linux integration checks, install the runtime prerequisites above.

The suite covers all 30 registry workspaces, request/response binding, symlink/FIFO/
hardlink and parent-replacement attacks, deadline enforcement, credential
handling, child-process cleanup, and the real Problem 1 checker followed by a
fake judge. The live sandbox probe is opt-in and makes no provider call:

```bash
QTBENCH_LIVE_SANDBOX_SMOKE=1 \
  uv run --extra dev --locked python -m pytest -q \
  inference/tests/test_live_sandbox.py
```

Validation for this integration did not use a live `OPENAI_API_KEY` and made no
paid model calls. The real no-network sandbox preflight and an offline
real-checker-to-fake-judge round trip are tested separately.
