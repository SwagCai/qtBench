# Contributing problems to qtBench

Thank you for helping extend qtBench. This guide covers contributions of new
benchmark problems. Corrections to existing problems are also welcome; explain
the mathematical or reproducibility issue clearly and include a focused test
when the expected behavior is mechanically checkable.

## Propose the problem first

Open a GitHub issue before doing substantial implementation work. Include:

- the precise discovery task and references establishing the target identity
  or open question;
- the proposed task type: `t_statistic_discovery`,
  `q_statistic_discovery`, or `exchanging_bijection`;
- the object family, canonical encoding, public statistics, and function(s) a
  submission must provide;
- any known checker limitation or unavoidable route to a tautological answer.

Use the issue to agree on scope and reserve a stable numeric problem ID. Do not
renumber an existing problem. Review the current catalogue in
[`docs/problems.md`](docs/problems.md) and the selection criteria in
[`docs/problem_bank_plan.md`](docs/problem_bank_plan.md) before proposing an
addition.

## What makes a suitable problem

A contribution should:

- be a recognized open question or an established q,t-identity, with the exact
  relationship to the cited source stated honestly;
- ask for a natural statistic, witness, or bijection rather than an arbitrary
  finite lookup or coefficient matching;
- differ from existing entries in its object fibers or required identity, not
  only in presentation;
- have a finite, varied public range that can be scored exactly within the
  fixed limits described in [`docs/checker.md`](docs/checker.md);
- publish every target and case identity used for scoring, together with a
  documented, reproducible derivation; and
- avoid including a solution to the requested statistic or bijection.

If the benchmark task is a derived or weakened version of a source problem,
say so prominently. If automatic scoring cannot distinguish genuine solutions
from tautological ones, propose `expert_review` status and document why.

## Follow the repository layout

Start from [`problems/problem_template.md`](problems/problem_template.md) and
follow [`docs/problem_authoring.md`](docs/problem_authoring.md). Place the
problem at:

```text
problems/<task_type>/<problem_name>/
```

`problem_name` must be a descriptive snake-case slug. The problem needs a
separate stable integer `id`; the directory name is the descriptive `name`, not
the numeric ID.

At minimum, add:

- `problem.md`, with a self-contained statement, object encoding, public
  statistics, exact submission signature, scored range, scoring command, and a
  `References` section;
- `metadata.json`, including `evaluator_kind`, public cases, and scoring gates;
- `known_statistic.py` or `known_statistics.py` when statistics are public;
- `data/polynomials.json`, `data/q_equals_1.json`, and
  `data/instances.json`;
- `generate_data.py` and any problem-specific oracle or certification code;
- a scored checker adapter and focused tests; and
- matching entries in `problems/registry.json`, `docs/problems.md`, and the
  relevant task-type README.

Keep problem-specific generators, oracles, and notes in the problem directory.
Only genuinely reusable combinatorial code belongs in `src/qtbench/`. A shared
generator may live under `scripts/generate/` when more than one problem uses it
and [`docs/data_generation.md`](docs/data_generation.md) documents the command.

## Data and checker requirements

- Generate targets deterministically with exact integer or rational arithmetic
  whenever possible. Document any external dependency or separate certificate.
- Make every data file identify itself with matching `problem_id` and
  `problem_name` values. Keep terms canonical and sorted.
- Treat `data/instances.json` as an orientation sample unless it intentionally
  contains the complete scored corpus. Give a sample its own `instances_max_*`
  bound; the complete scored range belongs in `metadata.json` and
  `data/polynomials.json`.
- Keep generation code separate from scoring. The scored evaluator must use
  metadata and committed public targets; it must never import an oracle.
- Validate exact coefficients and all object-level identities. A numerically
  correct submission must then pass fresh-namespace shuffled replay, the value
  audit, and deterministic large-object resource probes.
- Record a new checker attack or confirmed bypass in
  [`docs/cheating/taxonomy.md`](docs/cheating/taxonomy.md), with a regression
  test when the behavior is mechanically enforceable.

Passing the checker is necessary, not sufficient, evidence of a genuine
mathematical discovery. Do not claim that the checker proves naturalness.

## Validate the contribution

Create the locked development environment:

```bash
uv sync --extra dev --locked
```

Regenerate the problem's data using the command documented in
[`docs/data_generation.md`](docs/data_generation.md), then review the generated
diff. Run focused tests while developing and the complete suite before opening
the pull request:

```bash
uv run --extra dev --locked pytest -q
```

Also run the exact scored-evaluator command shown in `problem.md` against an
appropriate scorer-compatible fixture. The command, `metadata.json`
`evaluator_kind`, and checker dispatch must agree.

## Pull-request checklist

Prefer one new problem per pull request. In the description:

- link the proposal issue and primary mathematical references;
- summarize the task, public range, object counts, and reproduction command;
- state whether `instances.json` is a sample or the complete scored corpus;
- report the data-generation, evaluator, and test commands you ran; and
- disclose derivation exceptions, checker limitations, and any nonstandard
  dependencies.

Keep the pull request limited to the problem and the catalogue, evaluator, and
tests it requires. By contributing, you agree that your contribution is
licensed under this repository's [`LICENSE`](LICENSE); submit only material you
have the right to distribute.
