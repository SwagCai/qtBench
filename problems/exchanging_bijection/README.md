# Bijection discovery

Problems in this folder give public weights or statistics on combinatorial
object families and ask for a **bijection**. A submission defines `forward(object)` and
`inverse(object)`, and the evaluator checks that they are mutually inverse, that
they satisfy the identities the problem requires, and that the induced joint
distribution matches the target q,t-polynomial. Unlike statistic-discovery
tasks, nothing is withheld: both statistics are public. The unknown is the
bijection.

Five of the nine problems ask for a bijection that **exchanges** two statistics,

```text
stat_1(pi) = stat_2(forward(pi))
stat_2(pi) = stat_1(forward(pi))
```

which is a combinatorial proof of the q,t-symmetry of the target.

This folder currently holds nine problems:

- id `2`, `dyck_area_bounce_exchange`: a bijection on Dyck paths exchanging
  `area` and `bounce`, i.e. a combinatorial proof of the q,t-Catalan symmetry.
- id `4`, `polyomino_area_bounce_exchange`: a bijection on parallelogram
  polyominoes (of each `m x n` bounding box) exchanging `area` and `bounce`, i.e.
  a combinatorial proof of the q,t-Narayana symmetry -- the Narayana refinement
  of the q,t-Catalan case.
- id `5`, `polyomino_area_bounce_transpose`: a bijection on parallelogram
  polyominoes sending each `m x n` box to its transpose `n x m` while
  **preserving** `area` and `bounce`, i.e. a combinatorial proof of the
  q,t-Narayana symmetry in the two size parameters,
  `Nara_{m,n}(q,t) = Nara_{n,m}(q,t)`.
- id `24`, `macdonald_fillings_inv_maj_exchange`: a conjugate-shape bijection
  on standard HHL fillings exchanging `inv` and `maj`, giving a direct proof of
  Macdonald q,t-symmetry on every square-free monomial coefficient.
- id `25`, `parking_area_dinv_exchange`: a bijection on classical parking
  functions exchanging `area` and `dinv`, giving a direct proof of q,t-symmetry
  for the diagonal-coinvariant Hilbert series.
- id `26`, `graph_sibling_tuft_exchange`: a reduction-preserving bijection on
  unlabeled simple connected graphs exchanging the sibling and tuft numbers.
- id `28`, `shifted_setvalued_pq_weight_bijection`: the content-preserving map
  between the signed disjoint unions of set-valued shifted P- and Q-tableaux in
  Chiu--Marberg Corollary 4.1.
- id `29`, `andrews_bressoud_successive_rank_bijection`: a weight-preserving
  map between bounded-successive-rank partitions and residue-avoiding
  partitions in the Andrews--Bressoud theorem.
- id `30`, `improper_partition_matrix_inversion_sequence_bijection`: the
  semi-weight/distinct-entry preserving map from improper partition matrices to
  restricted inversion sequences in Chern--Fu Question 5.5.

## Non-exchange problems `5`, `28`, `29`, and `30`

Problem `5` is **not** an exchanging bijection. Its statistics are preserved
rather than exchanged, and its bijection goes between two different object sets
`Polyo_{m,n} -> Polyo_{n,m}` rather than from a set to itself. Its interface and
scoring nevertheless match the other bijection problems: two public statistics, an
unknown bijection given as `forward`/`inverse`, identities checked pointwise on
every public object, and the same gate order.

It is filed here because a folder holding a single problem would be a category
in name only. The repository's rule is that a distinction which can be a field
should not become a directory. Instead, the distinction is recorded where it is
checkable: `metadata.json` names the numerical gate
`transpose_identities_and_distribution` rather than
`area_bounce_identities_and_distribution`, the evaluator kind is
`polyomino-transpose`, and `problem.md` states the identities in full. If a
second transpose problem is added, the folder can be split then.

The obvious geometric transpose -- reflecting a polyomino across
the main diagonal -- preserves `area` but not `bounce`, so it is not a
solution.

Problem `28` likewise preserves a weight rather than exchanging two scalar
statistics, and its source and target are different disjoint unions. The
checker enforces the stronger complete content vector, not just total degree.

Problems `29` and `30` also join different object classes. Problem `29`
preserves ordinary-partition weight; problem `30` equates partition-matrix
semi-weight with inversion-sequence distinct-entry count.

## Task

Both statistics are given. The goal is an algorithmic bijection that extends
to all sizes -- and to all bounding boxes for problems `4` and `5` -- rather
than a size-by-size matching. The established symmetry makes the
`(stat_1, stat_2)` bags equinumerous, so one can always rank-match within them to
satisfy the identities. Such a construction assumes the symmetry
rather than proving it, gives no combinatorial insight, and is not an answer to
the task. The checker rejects the cheapest such attempts but
cannot certify genuineness on its own -- passing is necessary, not sufficient
(see `docs/checker.md`).

## Files

Each problem directory contains:

- `problem.md`: the mathematical statement, object encoding, the two public
  statistics, scoring rule, and references.
- `metadata.json`: machine-readable metadata (numeric id, name, task type,
  object family, public range, scoring rule, submission signature).
- `known_statistics.py`: reference implementations of the public statistics or
  grading.
- `data/polynomials.json`: the public target joint q,t-distribution.
- `data/q_equals_1.json`: the public `q = 1` specialization (a necessary
  marginal condition).
- `data/instances.json`: public objects with both statistic values. It is
  usually a sample covering fewer fibers than the scored range; problem `26`
  publishes its complete compact scored corpus. The scored range is the one in
  `data/polynomials.json` and is reproduced by the public generator. Problems
  `4` and `5` share `scripts/generate/generate_polyomino_data.py`; the other
  problems use an adjacent generator.

## Reading the data

`data/polynomials.json` lists one case per object fiber, each with `terms` of the
form `[stat_1_exponent, stat_2_exponent, coefficient]` sorted lexicographically.
The first three problems use `area,bounce`; problem `24` uses `inv,maj`, problem
`25` uses `area,dinv`, and problem `26` uses `sibling_number,tuft_number`.
Problem `28` records entry count in this compatibility file while its identity
gate preserves the full content vector. Dyck,
parking, and graph cases are keyed by size, polyomino cases by bounding box
`(m,n)`, Macdonald fillings by partition shape, and problems `29` and `30` by
their theorem parameters or size.

## Quick check

```bash
# Dyck area/bounce (id 2)
uv run --frozen python scripts/evaluate/evaluate_scored_submission.py \
  area-bounce path/to/submission.py

# Parallelogram polyomino area/bounce (id 4)
uv run --frozen python scripts/evaluate/evaluate_scored_submission.py \
  polyomino-area-bounce path/to/submission.py

# Parallelogram polyomino m,n-transpose (id 5)
uv run --frozen python scripts/evaluate/evaluate_scored_submission.py \
  polyomino-transpose path/to/submission.py

# Macdonald filling inv/maj exchange (id 24)
uv run --frozen python scripts/evaluate/evaluate_scored_submission.py \
  macdonald-fillings path/to/submission.py

# Parking-function area/dinv exchange (id 25)
uv run --frozen python scripts/evaluate/evaluate_scored_submission.py \
  parking-area-dinv path/to/submission.py

# Connected-graph sibling/tuft exchange (id 26)
uv run --frozen python scripts/evaluate/evaluate_scored_submission.py \
  graph-sibling-tuft path/to/submission.py

# Shifted P/Q content-preserving bijection (id 28)
uv run --frozen python scripts/evaluate/evaluate_scored_submission.py \
  shifted-pq path/to/submission.py

# Andrews--Bressoud successive-rank bijection (id 29)
uv run --frozen python scripts/evaluate/evaluate_scored_submission.py \
  successive-rank path/to/submission.py

# Improper partition-matrix/inversion-sequence bijection (id 30)
uv run --frozen python scripts/evaluate/evaluate_scored_submission.py \
  partition-matrix-inversion path/to/submission.py
```

The scored command prints a short report and exits successfully only when every
gate passes.
