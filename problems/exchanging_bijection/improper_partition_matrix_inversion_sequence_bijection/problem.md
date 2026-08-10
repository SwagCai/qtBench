# Improper partition-matrix/inversion-sequence bijection

## Task

For every `n`, construct Chern and Fu's direct bijection

```text
rho_n : IPPM_n^- -> I_n^-(-,-,=)
```

such that the semi-weight of the partition matrix equals the number of distinct
entries in its image inversion sequence. The authors prove the refined
equidistribution analytically in Theorem 3.3 and pose precisely this bijection
as Question 5.5.

This is the benchmark's first partition-matrix and inversion-sequence problem.
It is not a parameter extension or restatement of the existing path, tableau,
permutation, graph, parking, ASM, or ordinary-partition entries.

## Source objects

A partition matrix on `[n]` is an upper-triangular square matrix of subsets of
`[n]`: its nonempty cells partition `[n]`, every row and column is nonempty, and
labels in earlier columns are smaller than labels in later columns. For
`1 < i < n`, an ascent or descent occurs when `i` and `i+1` share a column but
occupy different rows. It is proper when `i` has the same parity as the least
label in that column. `IPPM_n` contains matrices with no proper ascent or
descent, and the minus class requires the cell containing `n` to have odd
cardinality.

The encoding

```text
M;row(1),...,row(n);col(1),...,col(n)
```

uses one-based row and column indices. The semi-weight is the sum over columns
of the ceiling of half that column's cardinality.

## Target objects

An inversion sequence is `(e_1,...,e_n)` with `0 <= e_i < i`. The class
`I_n(-,-,=)` has no triple `i<j<k` with `e_i=e_k`; equivalently, a value occurs
once or in one adjacent pair. Its minus class also requires
`e_{n-1} != e_n`. It is encoded as

```text
I;e_1,...,e_n
```

and graded by the number of distinct entries.

The submission receives a `PartitionMatrixInversion` exposing `encoding`,
`side`, `n`, `size`, `rows`, `columns`, `entries`, `grading`, and
`feature_dict()`, and returns a canonical encoding string.

## Public data and scoring

The public target exhausts both sides for `3 <= n <= 9` and contains 4,983
source objects. `data/instances.json` is only an illustrative sample. Submit:

```python
def forward(obj) -> str:
    ...

def inverse(obj) -> str:
    ...
```

Score with:

```bash
uv run --frozen python scripts/evaluate/evaluate_scored_submission.py partition-matrix-inversion submission.py
```

The evaluator checks canonicality, size, grading, and both round trips from
every object on both sides, then repeats in a fresh shuffled namespace and on
large independently constructed deterministic extremes and seeded-random valid
objects. Passing is necessary, not sufficient for a natural bijection; public
rank matching can pass the finite checks but not the scalable identity probes.

## References

- Shane Chern and Shishuo Fu, "Signed counting of partition matrices",
  *Journal of Combinatorial Theory, Series A* 223 (2026), Paper 106213,
  https://doi.org/10.1016/j.jcta.2026.106213; author manuscript
  https://shanechern.github.io/publications/preprints/106.pdf. Theorem 3.3 gives
  the analytic refined equality, Section 5 states that a direct bijective proof
  remains open, and Question 5.5 asks for exactly the map scored here.
