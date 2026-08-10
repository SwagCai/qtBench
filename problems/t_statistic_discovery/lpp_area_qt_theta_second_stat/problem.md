# Labelled Parallelogram Polyomino Theta-Operator Area Partner

## Task

Find a statistic `statistic(polyomino)` on standardly labelled parallelogram
polyominoes such that the joint distribution

```text
sum_P q^area(P) t^statistic(P)
```

matches the target polynomial `F_{m,n}(q, t)` for every tested bounding box
`(m, n)`.

This `t_statistic_discovery` task publishes one statistic, the labelled `area`,
and asks for its `t`-partner.

The target is the "Hilbert series" of the Theta-operator symmetric function of
D'Adderio, Iraci, Le Borgne, Romero and Vanden Wyngaerd,

```text
F_{m,n}(q, t) = < Theta_{e_{m-1}} Theta_{e_{n-1}} e_1 , e_{1^{m+n-1}} >,
```

which the pairing with `e_{1^{m+n-1}} = h_{1^{m+n-1}}` restricts to the standardly
labelled polyominoes `stLPP(m, n)`. Their **Problem 7.13** asks for a statistic
`tstat` on all labelled parallelogram polyominoes `LPP(m, n)` realizing the full
symmetric-function identity

```text
Theta_{e_{m-1}} Theta_{e_{n-1}} e_1 = sum_{P in LPP(m,n)} q^area(P) t^tstat(P) x^P;
```

restricting to standard labellings gives exactly the scalar `q,t`-target above.
Setting `t = 1` recovers `sum_{P in stLPP(m,n)} q^area(P)`, which is **proven** in
that paper (via a sandpile-model bijection); the full `q,t` statistic remains
open. Because `F_{m,n}` is symmetric in `q` and `t`, the `q = 1` marginal (the
required distribution of the unknown partner) equals the `area` distribution.

## Objects

A **parallelogram polyomino** of size `m x n` is a pair of monotone North/East
lattice paths from `(0, 0)` to `(m, n)`: the upper (red) path starts North and
ends East, the lower (green) path starts East and ends North, and the two paths
touch only at the corners. A cell `(x, y)` spans `[x, x+1] x [y, y+1]`.

A cell is **labelled** when it carries a vertical step of the upper path (a *red*
cell) and/or a horizontal step of the lower path (a *green* cell):

- a North step of the upper path from `(x, y)` to `(x, y+1)` labels cell `(x, y)`;
- an East step of the lower path from `(x, y)` to `(x+1, y)` labels cell `(x, y)`.

Cell `(0, 0)` carries both (the *black* cell); there are exactly `m + n - 1`
labelled cells. A **standard labelling** is a bijection from the labelled cells to
`[m + n - 1]` whose labels are strictly increasing up each column and strictly
decreasing from left to right along each row. `stLPP(m, n)` is the set of such
objects.

An object is encoded as the string `upper + "|" + lower + "|" + labels`, where
`labels` lists the label of each labelled cell in the canonical `(x, y)` order
(columns first, then rows). For example the single-cell `1 x 1` polyomino is

```text
NE|EN|1
```

The Python submission receives a `LabelledParallelogramPolyomino` object with:

- `polyomino.m`, `polyomino.n`, `polyomino.size` (`= m + n - 1`)
- `polyomino.upper`, `polyomino.lower` (the two boundary words)
- `polyomino.labelled_cells` (triples `(x, y, label)` in canonical order)
- `polyomino.label` (map `(x, y) -> label`)
- `polyomino.red_cells`, `polyomino.green_cells`
- `polyomino.rows` (per row `y`, the `(x, label)` pairs left to right)
- `polyomino.columns` (per column `x`, the `(y, label)` pairs bottom to top)
- `polyomino.cells` (all cells enclosed by the two paths)
- `polyomino.area()`

## Public Statistic

The labelled `area` is the number of non-labelled cells `(x, y)` between the two
paths such that the nearest labelled cell to the left in row `y` carries a
strictly greater label than the nearest labelled cell below in column `x`:

```text
area(P) = #{ (x, y) enclosed, not labelled : left_label(x, y) > below_label(x, y) }.
```

The same algorithm is implemented in `known_statistic.py`.

## Public Data

`data/polynomials.json` contains the target `F_{m,n}(q, t)` for every bounding
box with `2 <= m + n <= 8`; each term is `[area_exponent, partner_exponent,
coefficient]`. The polynomials are `q,t`-symmetric and total `|stLPP(m, n)|`.
They are the Theta-operator Hilbert series above, computed in the maintainer
oracle and independently checked to reproduce the `area` distribution of
`stLPP(m, n)` at `t = 1`.

`data/q_equals_1.json` contains the `q = 1` specialization, the required
one-variable distribution of the unknown partner statistic (a necessary, not
sufficient, condition).

`data/instances.json` lists the public objects (`2 <= m + n <= 7`) with their
`area` values. It does not contain the target `t`-statistic.

**`data/instances.json` is a sample, not the scored set.** It lists 2,396 objects over 21 of the 28 scored fibers, while scoring runs over all 24,048 objects of the range in `data/polynomials.json`. Its `instances_max_*` field bounds that sample only. Enumerate the full scored range with `qtbench.combinatorics` before trusting a proposal.

## Submission

Submit a short, self-contained Python file defining:

```python
def statistic(polyomino) -> int:
    ...
```

The return value must be a nonnegative integer. See `docs/checker.md` for the
admission checks.

To score it:

```bash
uv run --frozen python scripts/evaluate/evaluate_scored_submission.py lpp path/to/submission.py
```

## Scoring

After the capability and source-economy screens, the evaluator enumerates each
public `stLPP(m, n)` box once. From the same submitted values, it checks the
explicit `q = 1` marginal and every `q,t` coefficient. Only a complete match
proceeds to fresh-namespace shuffled replay, the integer-value audit, and large
adversarial polyominoes under CPU and memory limits. A mismatch stops the
evaluation, and passing `q = 1` alone is insufficient. Every stage must pass,
though a pass is necessary but not sufficient for a genuine statistic (see
`docs/checker.md`).

## References
- Michele D'Adderio, Alessandro Iraci, Yvan Le Borgne, Marino Romero, and Anna Vanden Wyngaerd, "Tiered trees and Theta operators", International Mathematics Research Notices 2023, no. 24, 20748-20783, arXiv:2202.05706, https://arxiv.org/abs/2202.05706. States Problem 7.13 and proves the `t = 1` (area) case via the sandpile model.
- Michele D'Adderio, Alessandro Iraci, and Anna Vanden Wyngaerd, "Theta operators, refined Delta conjectures, and coinvariants", Advances in Mathematics 376 (2021), 107447, arXiv:1906.02623, https://arxiv.org/abs/1906.02623. Introduces the Theta operators `Theta_f`.
- Michele D'Adderio, Alessandro Iraci, and Anna Vanden Wyngaerd, "Decorated Dyck paths, polyominoes, and the Delta conjecture", arXiv:2011.09568, https://arxiv.org/abs/2011.09568. Defines the `pmaj` statistic on singly-labelled polyominoes that the conjectured partner should extend.
- James Haglund, Jeffrey B. Remmel, and Andrew T. Wilson, "The Delta Conjecture", Transactions of the American Mathematical Society 370 (2018), 4029-4057, https://doi.org/10.1090/tran/7096.
- Mark Dukes and Yvan Le Borgne, "Parallelogram polyominoes, the sandpile model on a complete bipartite graph, and a q,t-Narayana polynomial", Journal of Combinatorial Theory Series A 120 (2013), 816-842, arXiv:1208.0024, https://arxiv.org/abs/1208.0024. The sandpile technique relating polyomino area to the level statistic.
