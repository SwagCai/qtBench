# Problem authoring

Each benchmark problem should contain:

- `problem.md`: mathematical statement, object encoding, public statistic
  definitions, submission signature, scoring rule, and a `References` section
  for the papers defining the polynomials and problem.
- `metadata.json`: machine-readable task type, object family, public range,
  scoring rule, and entry point. It must carry `evaluator_kind`, the first
  argument to `scripts/evaluate/evaluate_scored_submission.py`. The same command
  must appear in `problem.md`; `tests/problems/test_registry.py` pins both to the
  CLI dispatch table. Because fiber parameters differ by problem, `public_cases`
  is descriptive per object family rather than a fixed schema.
- `known_statistic.py`: executable implementation of the known public statistic,
  exposing `statistic(obj) -> int`. A problem with two public statistics instead
  uses `known_statistics.py` and names one function per statistic. A problem with
  *no* public statistic, where the submission supplies every graded exponent,
  has neither file and sets `known_statistics: []` in `metadata.json`.
- `data/polynomials.json`: public canonical polynomial terms.
- `data/q_equals_1.json`: the specialization of the first grading variable to
  `1`, giving a necessary marginal distribution for the unknown statistic. The
  filename is conventional; for problems graded by `u = q - 1`, it means
  `u = 1`, not `q = 1`.
- `data/instances.json`: the public objects and their public statistics only,
  usually sampled for orientation. It may instead contain a complete compact
  scored range when that is useful to the checker; say which in `problem.md`.
  A smaller sample must have its own `instances_max_*` bound rather than
  reusing the scored `public_max_*` value with a different meaning.
- `generate_data.py` and any problem-specific oracle: public reproducibility
  code normally kept beside the problem. A generator shared by multiple problems,
  such as the polyomino generator for problems `4` and `5`, may live under
  `scripts/generate/` when [`data_generation.md`](data_generation.md) documents
  the shared entry point. A committed-target re-emitter such as problem `3` must
  state clearly that it is not an independent derivation. If exact certification
  requires a separate tool, include that tool and a target-bound certificate in
  `data/`.

Every scored problem also needs a checker adapter under `src/qtbench/` that:

- validates the trusted object representation and its size parameter;
- performs its public numerical comparisons in one object-enumeration pass;
- accepts an optional secret order seed so each public fiber can be replayed
  with a single-cycle shuffle from a fresh submission namespace;
- generates deterministic extremal and post-submission random resource probes;
- runs any applicable public marginal checks and object-level
  validity/inverse/statistic identities before comparing the complete
  polynomial; and
- uses `evaluate_*_submission`, never `evaluate_submission_file`,
  `load_statistic_function`, or other unrestricted module loading, for scoring.
  Those diagnostic APIs execute supplied local files with the caller's
  privileges and must be used only with trusted inputs; untrusted use requires
  an external operating-system sandbox.

Adding polynomial data without this adapter is not enough to make a problem
scoreable.

Place each problem under one of:

- `problems/t_statistic_discovery/` (whatever the number of public statistics:
  one, two as in problem `12`, or none as in problem `13`)
- `problems/q_statistic_discovery/`
- `problems/exchanging_bijection/` (any bijection task; problems `5` and `28`--`30`
  preserve public data between different source and target sets rather than
  exchanging two statistics)

Every problem must have both a stable numeric `id` and a descriptive `name`.
Use the number for `id`, for example `1`, and the snake-case slug for `name`,
for example `nc_area_qt_narayana_second_stat`. Do not use the long descriptive
slug as the problem id.

The public problem directory must match `name`, and `task_type` must match its
containing directory. Thus, `problems/<task_type>/<name>/` holds without
exception (`tests/problems/test_registry.py` asserts it). Do not add a task type
for a distinction that could be a field instead: the number of public statistics
is data, carried by `known_statistic` or `known_statistics`.

`metadata.json` and registry entries carry the numeric id as `id` and the
descriptive name as `name`. Public JSON files under `data/` carry the same values
under the fully qualified keys `problem_id` and `problem_name`, so each target
identifies itself when read on its own. `tests/problems/test_registry.py` asserts
that all three agree.

The registry `status` describes how a result may be interpreted: use `active`
for automatically scored discovery tasks, `calibration` for solved pipeline
fixtures, `expert_review` when no automatic verdict is available, and `draft` or
`retired` only for explicitly retained non-current catalogue entries.

Do not publish a solution to the requested statistic. A target-generation oracle
is different: keep it public in the problem directory for reproducibility, while
ensuring that scoring uses only metadata and public target data and never imports
the oracle.

## Repository layout hygiene

Keep every problem-specific file under its task category and problem name:

```text
problems/<task_category>/<problem_name>/
```

Keep problem-specific generators, oracles, and notes in the problem directory.
A generator genuinely shared by multiple problems may instead live under
`scripts/generate/`; problems `4` and `5` are the current example, and their
shared command is documented in [`data_generation.md`](data_generation.md).
A problem-specific oracle should live at a path such as:

```text
problems/t_statistic_discovery/nc_area_qt_narayana_second_stat/oracle.py
```

Oracle modules should declare both `PROBLEM_ID = <id>` and
`PROBLEM_NAME = "<problem_name>"` near the top. Shared reusable code belongs under
`src/qtbench/`, not under a problem directory.

## Public target scoring

All target polynomial terms and case identities used for scoring are public.
After capability and source-economy screens, the scored path compares any
applicable public marginal and every generated coefficient exactly. A mismatch
stops immediately. A numerical match is then replayed in a fresh namespace and secret
shuffled order to verify referential transparency before the integer-value audit
and adversarial time/memory probes (see `checker.md`).

The public range should be large and varied enough to test the mathematical
proposal. Its complete numerical comparison and fresh shuffled replay must fit
the [fixed official scoring configuration](checker.md#stages): a 60-second
numerical timeout and a 192 MiB worker-process ceiling, with a 64 MiB reserve
for the evaluator parent inside a 256 MiB aggregate process envelope. Resource
probes should be much larger while remaining cheap for the trusted object
generator.
Target secrecy is not an anti-cheating mechanism, and passing the checker is
only a necessary condition for a genuine result.

Document new checker attacks and confirmed bypasses in
`cheating/taxonomy.md`, with a focused regression test when the expected
behavior is mechanically enforceable.

Canonical bivariate terms have the form:

```json
[q_exponent, t_exponent, coefficient]
```

A target uses one exponent per grading variable, so a trivariate one (two public
statistics plus the missing one) has terms of the form:

```json
[q1_exponent, q2_exponent, q3_exponent, coefficient]
```

A target may also be graded by a partition that is read off the object rather
than submitted -- the shape of a tableau, the e-composition of a path. That
index leads the term, so problem `14` uses `[partition, q_exponent, coefficient]`
and problems `18` and `20` use `[partition, u_exponent, t_exponent, coefficient]`.
