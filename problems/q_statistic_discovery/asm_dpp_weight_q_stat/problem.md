# Alternating-sign-matrix DPP weight statistic

## Task

For every alternating sign matrix `A`, define a nonnegative integer statistic
`dpp_weight(A)` such that, for each `n`,

```text
sum_{A in ASM(n)} q^dpp_weight(A)
  = sum_{D in DPP(n)} q^sum_of_parts(D)
  = product_{k=0}^{n-1} [3k+1]_q! / [n+k]_q!.
```

This is exactly Open Problem 1.4 in Dennis Stanton's *Some Problems*: find a
statistic on `ASM(n)` whose generating function is `DPP(n,q)`. The polynomial
is already a positive enumerator—its coefficient of `q^d` counts descending
plane partitions with largest part at most `n` and total sum of parts `d`—but
no statistic on alternating sign matrices is known.

The problem is substantively different from the existing path, tableau,
partition, matching, tree, parking-function, and graph tasks: it is the first
benchmark problem on alternating sign matrices, and its target comes from the
unresolved ASM--descending-plane-partition correspondence.

## Objects

An `n` by `n` alternating sign matrix has entries in `{-1,0,1}`; every row and
column sums to one, and its nonzero entries alternate in sign. It is encoded as
`n:` followed by its rows separated by `/`, using `-`, `0`, and `+` for the
three entries. For example,

```text
3:0+0/+-+/0+0
```

is the unique non-permutation matrix in `ASM(3)`.

The submission receives an `AlternatingSignMatrix` with `matrix.encoding`,
`matrix.n`, `matrix.size`, `matrix.rows`, `matrix.negative_count`,
`matrix.inversion_number`, and `matrix.feature_dict()`.

## Public data and scoring

`data/polynomials.json` gives the complete DPP weight enumerator for
`1 <= n <= 7`, covering `1, 2, 7, 42, 429, 7436, 218348` ASMs. The adjacent
generator independently enumerates descending plane partitions to obtain each
coefficient and alternating sign matrices via monotone triangles to verify the
fiber sizes. `data/instances.json` is a sample, not the scored set: it lists all
ASMs only through `n = 4`.

Submit a short, self-contained Python file defining:

```python
def statistic(matrix) -> int:
    ...
```

Run:

```bash
uv run --frozen python scripts/evaluate/evaluate_scored_submission.py asm-q path/to/submission.py
```

After capability and source-economy screening, the evaluator checks the exact
distribution on every public size and repeats it in a fresh namespace with a
secret single-cycle order. It then checks independently generated permutation
and non-permutation ASMs at sizes far beyond the public range under fixed time
and memory limits.

Passing is necessary, not sufficient for a genuine solution. A uniform ranking
construction can reproduce a public distribution without explaining the DPP
weight; see `docs/checker.md`.

## References

- Dennis Stanton, *Some Problems* (2019), Open Problem 1.4,
  https://www-users.cse.umn.edu/~stant001/PAPERS/Prob2019.pdf. It explicitly
  asks for a statistic on `ASM(n)` with generating function `DPP(n,q)`.
- Roger E. Behrend, Philippe Di Francesco, and Paul Zinn-Justin, "On the
  weighted enumeration of alternating sign matrices and descending plane
  partitions", Journal of Combinatorial Theory, Series A 119 (2012), 331--363,
  arXiv:1103.1176, https://arxiv.org/abs/1103.1176. It defines ASMs, DPPs, and
  their established refined correspondence, and records the DPP sum-of-parts
  product while noting that no ASM counterpart is known.
- Michael J. Schlosser, "A local bijection between alternating sign matrices
  and descending plane partitions and a Striker--Fulmek-type q-statistic",
  arXiv:2606.13653 (withdrawn, 2026), https://arxiv.org/abs/2606.13653. The
  author withdrew the claimed statistic and bijection because essential
  all-order steps lacked a complete human-verifiable proof; its main theorem is
  explicitly not established.
