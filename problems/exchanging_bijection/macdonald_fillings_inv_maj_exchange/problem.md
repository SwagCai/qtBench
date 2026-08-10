# Macdonald standard-filling inv/maj exchanging bijection

## Task

For every non-hook partition `mu`, construct mutually inverse maps between the standard
fillings of `mu` and those of its conjugate `mu'` that exchange the
Haglund--Haiman--Loehr statistics:

```text
forward(F) has shape mu'
inv(F) = maj(forward(F))
maj(F) = inv(forward(F))
```

and the analogous identities for `inverse`. Such a bijection gives a direct
combinatorial proof, on the square-free monomial coefficient, of the Macdonald
symmetry

```text
H~_mu(X;q,t) = H~_{mu'}(X;t,q).
```

The identity follows algebraically from transformed Macdonald polynomials, but
a uniform bijection on fillings is not known. Gillespie solves the full exchange
for hook shapes, which are deliberately excluded from scoring, and handles only
one-variable specializations or restricted families beyond them. Problem 1.15
asks for the general exchange, and Problem 6.43 asks for an all-shapes extension
of the map used in the Hall--Littlewood case. In particular, Gillespie's
all-shapes square-free result is only for the Hall--Littlewood (`q = 0`)
specialization. Gillespie--Kaliszewski--Morse prove the specialization at
`q = 1`, not the full two-statistic exchange. The probabilistic entry-swapping
maps of Dantas e Moura--Mandelshtam address a different non-attacking-filling
symmetry and do not give this deterministic conjugate-shape exchange.

This is distinct from problem `13`, which asks for two unknown statistics on
standard Young tableaux realizing modified Kostka--Macdonald coefficients. Here
the objects are all `n!` bijective fillings of a fixed diagram, both HHL
statistics are public, and the unknown is a conjugate-shape bijection satisfying
two pointwise identities.

## Objects

A standard filling of a Young diagram of partition shape
`mu = (mu_1, ..., mu_r)` puts `1, ..., n` bijectively in its `n = |mu|` cells;
there is no row or column monotonicity condition. We use French notation and
list rows from bottom to top. The encoding is

```text
shape|bottom_row/next_row/.../top_row
```

with commas within the shape and rows. For example:

```text
2,2|1,3/4,2
```

The submission receives a `StandardMacdonaldFilling` with `encoding`, `shape`,
`conjugate_shape`, `rows`, `n`, `size`, `inv()`, and `maj()`. It returns the
canonical string encoding of the image.

## Public Statistics

Read every column from top to bottom. `maj(F)` is the sum of the ordinary major
indices of those column words. Equivalently, every cell whose entry is larger
than the one immediately below contributes one plus the number of cells above
it in its column.

Two cells attack when they lie in the same row, or in adjacent rows with the
upper cell strictly to the right of the lower cell. Orient a same-row pair from
left to right and an adjacent-row pair from the upper cell to the lower cell.
An attacking inversion occurs when the first entry is larger than the second.
Then

```text
inv(F) = number of attacking inversions
         - sum of the arm lengths of descent cells.
```

Both implementations are public in `known_statistics.py` and on the object.

## Public Data

`data/polynomials.json` gives `sum_F q^inv(F) t^maj(F)` for every non-hook
partition shape with `4 <= n <= 8`. This is 30 shapes and 608,664 scored fillings.
`data/q_equals_1.json` gives the `maj` marginal. `data/instances.json` lists all
fillings through `n = 5` with both public statistics; it is a sample, not the scored set.

The adjacent generator enumerates the standard fillings and recomputes every
target directly from the public statistics. It also checks shape-by-shape that
the conjugate distribution is obtained after exchanging the two exponents.

## Submission

Submit a short, self-contained Python file defining:

```python
def forward(filling) -> str:
    ...

def inverse(filling) -> str:
    ...
```

To score it:

```bash
uv run --frozen python scripts/evaluate/evaluate_scored_submission.py macdonald-fillings path/to/submission.py
```

## Scoring

After capability and source-economy screening, the evaluator enumerates every
public shape once. It checks valid conjugate-shape images, both round trips,
both inv/maj exchange identities, and the complete public distribution. Only a
complete match proceeds to fresh-namespace shuffled replay, the integer-value
audit, and large standard fillings under CPU and memory limits, where the same
pointwise identities are checked without a target. Every stage must pass.

Passing is necessary, not sufficient for a genuine bijection: uniform rank
matching between equinumerous `(inv,maj)` fibers would pass while assuming the
Macdonald symmetry it is supposed to explain. See `docs/checker.md`.

## References

- James Haglund, Mark Haiman, and Nicholas Loehr, "A combinatorial formula for
  Macdonald polynomials", Journal of the American Mathematical Society 18
  (2005), 735--761, arXiv:math/0409538,
  https://arxiv.org/abs/math/0409538. Defines the filling formula and the
  `inv` and `maj` statistics.
- Maria Monks Gillespie, "A combinatorial approach to the q,t-symmetry in
  Macdonald polynomials", Electronic Journal of Combinatorics 23(2) (2016),
  P2.38, arXiv:1503.02109, https://arxiv.org/abs/1503.02109. Studies the filling
  bijection, handles restricted shapes and specializations, and poses the
  general exchange and all-shapes Hall--Littlewood extension in Problems 1.15
  and 6.43.
- Maria Gillespie, Ryan Kaliszewski, and Jennifer Morse, "Macdonald symmetry at
  q=1 and a new class of inv-preserving bijections on words", Séminaire
  Lotharingien de Combinatoire 78B (2017), Article 27, arXiv:1611.04973,
  https://arxiv.org/abs/1611.04973. Gives a direct bijection at the `q = 1`
  specialization; the full `q,t` exchange remains open.
- Guilherme Zeus Dantas e Moura and Olya Mandelshtam, "Probabilistic Entry
  Swapping Bijections for Non-Attacking Fillings", arXiv:2503.06051,
  https://arxiv.org/abs/2503.06051. Gives probabilistic maps for a distinct
  permuted-basement Macdonald symmetry, not the deterministic HHL `inv`/`maj`
  conjugation map requested here.
