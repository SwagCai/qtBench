# Reproducing public data

Most public target-emission entry points live beside each problem's `problem.md`,
as do the derivation oracles when they are available. Problems `4` and `5` use
the shared generator described below. Generators write
`data/polynomials.json`, `data/q_equals_1.json`, and `data/instances.json`.
They are reproducibility tools only: the scored evaluator never imports them.
Problem 3 is the exception where the entry point re-emits committed target
records but the underlying derivation pipeline is not included; see below.

The generator entry points are Python files, but the snippets below use POSIX shell
syntax (`\` continuations, `$problem`, and `for ... do`). In PowerShell, put a
continued command on one line, assign paths with `$problem = "..."`, and run
the two problem `4`/`5` generator commands separately instead of using the loop.

Create the locked environment with the generation dependencies:

```bash
uv sync --extra generation --locked
```

Every problem-local generator emits its published range with no options:

```bash
uv run --extra generation --locked python \
  problems/<task_type>/<problem_name>/generate_data.py
```

Run `--help` before changing a public range. `--problem-dir` remains available
for clean-room reproduction in a copied problem directory; that directory must
already contain the matching `metadata.json` and any adjacent source inputs or
oracle required by the generator. For problem `1` and problems `6`--`23`, the
generator imports and executes that adjacent oracle with the caller's privileges
and no checker resource boundary. The copied directory must therefore be trusted;
use an external operating-system sandbox for untrusted input. Generation
overwrites the three public JSON files, so review the resulting diff. The
following cases need additional context.

Problems `24`, `25`, `26`, `28`, `29`, and `30` use only their public combinatorial structures: their
local generators enumerate the scored fibers, form the joint distributions,
and assert the required q,t-symmetry directly. Problem `26` obtains the
complete graph atlas through NetworkX and additionally checks symmetry inside
every reduction fiber. They need no problem-specific oracle.

Problem `28` independently enumerates both signed unions in Chiu--Marberg
Corollary 4.1 for each fixed shape and content and asserts exact fiber equality.

Problem `29` independently filters ordinary partitions by the bounded-rank and
residue-avoidance conditions in the Andrews--Bressoud theorem. Problem `30`
independently filters all partition matrices and inversion sequences by the two
minus-class definitions in Chern--Fu Question 5.5. Both generators assert exact
equality of the complete public grading distributions.

Problem `27` independently enumerates descending plane partitions by their sum
of parts for the target and alternating sign matrices through monotone triangles
for the object-count check.

## Problem 1

The noncrossing-partition generator defaults to the adjacent public `oracle.py`:

```bash
problem=problems/t_statistic_discovery/nc_area_qt_narayana_second_stat
uv run --extra generation --locked python "$problem/generate_data.py"
```

The `--statistic-module` option can be used to test another trusted local oracle
explicitly. It imports and executes the supplied file with the caller's
privileges and no checker resource boundary; use an external operating-system
sandbox for untrusted input.

## Problems 4 and 5

The two polyomino bijection problems share the same objects and target data, so
they use a common generator under `scripts/generate/`:

```bash
for problem in \
  problems/exchanging_bijection/polyomino_area_bounce_exchange \
  problems/exchanging_bijection/polyomino_area_bounce_transpose
do
  uv run --extra generation --locked python \
    scripts/generate/generate_polyomino_data.py --problem-dir "$problem"
done
```

## Problem 3

The Type B generator reads the committed `source_data/` records beside it. It
re-emits the recorded polynomials and verifies their total, q,t-symmetry, and
area marginal; it is not an independent derivation. The `n = 1` cyclic value
and `n = 2,3,4` Stump-table values have the stated external provenance. The
`n = 5,6` targets are reported direct-computation outputs, but their computation
code and raw work records are absent. The `n = 7,8,9` targets remain conditional
SL2-string completions, but the reconstruction program and raw solver records
needed to repeat their selection are also absent. In particular, `source_file`
values under `work/` in the partial-coefficient JSON are provenance labels for
files not shipped in this repository. See the problem's `source_data/README.md`.

## Problem 15

The ordinary generator uses two independent prime fields for fast rank
computation and exact rational elimination on the smaller validation range:

```bash
problem=problems/q_statistic_discovery/inv_orbit_harmonics_hilbert_q_stat
uv run --extra generation --locked python "$problem/generate_data.py"
```

The scored range is certified separately over `QQ` using proof-enabled SageMath
sparse elimination. This step requires a SageMath installation that provides
`sage.all`. Check with `sage -python -c 'import sage.all'` before running it:
modular repackagings such as passagemath provide `sage.all` only after the
relevant component packages are installed. Nothing else in the repository
requires SageMath.
The shipped `data/exact_certificate.json` records the build that produced it:

```bash
problem=problems/q_statistic_discovery/inv_orbit_harmonics_hilbert_q_stat
sage -python "$problem/certify_exact.py"
```

That command covers every public `(n,a)` case through `n = 10` and writes
`data/exact_certificate.json`, including the SHA-256 digest of
`data/polynomials.json`. It is substantially slower than the ordinary generator.
