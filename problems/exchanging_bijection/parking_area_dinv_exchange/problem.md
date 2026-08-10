# Parking-function area/dinv exchanging bijection

## Task

Construct mutually inverse maps on classical parking functions of every length
that exchange `area` and `dinv`:

```text
area(p) = dinv(forward(p))
dinv(p) = area(forward(p)).
```

The benchmark asks for an arbitrary bijection with an explicit inverse. The
stronger involution problem would additionally require `forward = inverse`.
Either construction gives a direct combinatorial proof of the q,t-symmetry of
the Hilbert series of diagonal coinvariants.

McCammond--Thomas--Williams call this a long-standing open problem and state
that it remains wide open even for the alternating subspace. The one-variable
zeta map proves only the equidistribution obtained after forgetting one of the
two statistics; it does not exchange both statistics pointwise.

This is not the Dyck-path area/bounce problem `2`. Parking functions are labelled
objects: there are `(n+1)^(n-1)` rather than Catalan-many of size `n`, `dinv`
depends on the car labels, and the target is the full diagonal-coinvariant
Hilbert series rather than the q,t-Catalan polynomial. Problem `12` also uses
parking functions, but only inside Tamari-ordered pairs and asks for a missing
third statistic in a different trivariate distribution. It neither asks for nor
supplies an area/dinv exchanging bijection.

## Objects

A classical parking function of length `n` is a word
`p = (p_1, ..., p_n)` of nonnegative integers whose increasing rearrangement
`b_1 <= ... <= b_n` satisfies `b_i <= i-1`. It is encoded as comma-separated
values, for example:

```text
2,0,1,0
```

The submission receives a `ParkingFunction` with `encoding`, `values`, `shape`,
`n`, `size`, `area()`, and `dinv()`, and returns a canonical encoding string.

## Public Statistics

The shape `beta(p)` is the increasing rearrangement of the word. Its area is

```text
area(p) = binom(n,2) - sum_i beta_i.
```

For `dinv`, lexicographically sort `(p_i, i)` by preference and let `a_j` be the
car label and `c_j = j - p_{a_j}` in the resulting order. Then `dinv(p)` counts
pairs `i < j` satisfying either

```text
c_i = c_j     and a_i < a_j,
```

or

```text
c_i - c_j = 1 and a_i > a_j.
```

The public implementations are in `known_statistics.py` and on the object.

## Public Data

`data/polynomials.json` gives

```text
sum_p q^area(p) t^dinv(p)
```

for `1 <= n <= 7`, covering 280,392 scored parking functions.
`data/q_equals_1.json` gives the `dinv` marginal. `data/instances.json` lists all
objects through `n = 5` with both statistics; it is a sample, not the scored set.
The adjacent generator enumerates every public object, recomputes the target,
and verifies its q,t-symmetry.

## Submission

Submit a short, self-contained Python file defining:

```python
def forward(parking) -> str:
    ...

def inverse(parking) -> str:
    ...
```

To score it:

```bash
uv run --frozen python scripts/evaluate/evaluate_scored_submission.py parking-area-dinv path/to/submission.py
```

## Scoring

After capability and source-economy screening, the evaluator checks every public
parking function for valid same-size images, both round trips, both exchange
identities, and the complete public distribution. A complete match is replayed
from a fresh namespace in a secret single-cycle order, followed by the
integer-value audit and pointwise identity checks on large parking functions
under CPU and memory limits. Every stage must pass.

Passing is necessary, not sufficient for a genuine bijection. A uniform
rank-matching construction inside equinumerous statistic fibers would pass while
assuming the symmetry it is meant to explain. See `docs/checker.md`.

## References

- Jon McCammond, Hugh Thomas, and Nathan Williams, "Fixed points of parking
  functions", Transactions of the American Mathematical Society 372 (2019),
  8473--8495, arXiv:1901.02906, https://arxiv.org/abs/1901.02906. Section 1.4
  states the area/dinv involution problem and distinguishes it from the
  one-variable zeta map.
- Erik Carlsson and Anton Mellit, "A proof of the shuffle conjecture", Journal
  of the American Mathematical Society 31 (2018), 661--697,
  arXiv:1508.06239, https://arxiv.org/abs/1508.06239. Proves the parking-function
  formula for diagonal coinvariants from which the q,t-symmetry follows.
- James Haglund and Nicholas Loehr, "A conjectured combinatorial formula for the
  Hilbert series for diagonal harmonics", Discrete Mathematics 298 (2005),
  189--204, https://doi.org/10.1016/j.disc.2004.01.022. Introduces the relevant
  parking-function area and dinv formula.
