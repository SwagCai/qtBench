# Andrews--Bressoud successive-rank weight-preserving bijection

## Task

Fix integers `M,r` with `0 < r < M/2`. Construct mutually inverse,
weight-preserving maps between:

1. partitions whose successive ranks all lie in
   `[2-r, M-r-2]`; and
2. partitions with no part congruent to `0`, `r`, or `-r` modulo `M`.

This is the bijective form of the Andrews--Bressoud partition theorem. Its
equality is proved analytically, but no bijective proof is known in general.
The public cases deliberately exclude `M=5`: its two Rogers--Ramanujan
specializations already have Garsia--Milne bijections.

This is substantively different from every prior qtBench entry. Its objects are
ordinary integer partitions, its fibers are cut out by Durfee-diagram ranks or
congruence exclusions, and the required map preserves partition weight. It is
not a rectangular, Catalan, path, graph, parking, or tableau variant.

## Objects and encoding

For a partition `lambda` with conjugate `lambda'`, its `i`th successive rank is
`lambda_i - lambda'_i`, for every diagonal cell `i`. Source objects use

```text
S;M;r;lambda_1,lambda_2,...
```

and target objects use the same encoding beginning with `T`. Parts are positive
and weakly decreasing, without leading zeroes. For example,
`S;7;2;5,3,1` is valid exactly when its successive ranks lie in `[0,3]`.
The submission receives a `SuccessiveRankPartition` exposing `encoding`,
`side`, `modulus`, `residue`, `parts`, `ranks`, `weight`, `size`, and
`feature_dict()`, and returns a canonical encoding string.

## Public data and scoring

The twelve public fibers use `(M,r) = (6,1), (6,2), (7,2), (7,3)` and weights
`12,20,28`. `data/polynomials.json` records their exact counts;
`data/instances.json` is an illustrative sample, not the scored set. The
adjacent generator reconstructs both complete sides from ordinary partitions
and verifies equality before writing the data.

Submit a short, self-contained Python file defining:

```python
def forward(partition) -> str:
    ...

def inverse(partition) -> str:
    ...
```

Score it with:

```bash
uv run --frozen python scripts/evaluate/evaluate_scored_submission.py successive-rank submission.py
```

The evaluator checks every object on both sides for canonical output, unchanged
`M`, `r`, and weight, and both round trips. It then performs fresh-namespace
shuffled replay and large independently constructed source and target probes,
including a deterministic rectangle/all-ones pair and a seeded-random pair.
Passing is necessary, not sufficient for a genuine bijection: rank matching in
the public fibers can pass finite checks, while the large gates make direct
enumeration uneconomic.

## References

- Alexander Burstein, Sylvie Corteel, Alexander Postnikov, and Carla D. Savage,
  "A lattice path approach to counting partitions with minimum rank t",
  *Discrete Mathematics* 249 (2002), 31--39,
  https://doi.org/10.1016/S0012-365X(01)00225-4. The introduction states the
  full Andrews--Bressoud theorem and explicitly says that no bijective proof is
  known.
- Sylvie Corteel, Sergi Elizalde, and Carla D. Savage, "Partitions with
  constrained ranks and lattice paths", *Enumerative Combinatorics and
  Applications* 3:3 (2023), Article S2R18,
  https://doi.org/10.54550/ECA2023V3S3R18. This
  later paper gives bijections for a one-sided limiting corollary and restates
  the finite two-sided theorem; it does not provide the map requested here.
