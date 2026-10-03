# Selected-Area gamma-Parking Function Delta-Xi Partner

## Task

Find a statistic `statistic(selection)` on pairs `(p, S)` of a gamma-parking
function and a subset of its area cells such that

```text
sum_{p : eta(p) = eta} sum_{S subset Area(p)} u^#S t^statistic(p, S)
```

equals `c_eta^shift(u, t)` for every tested pair of partitions `(gamma, lambda)` and
every partition `eta`.

This `t_statistic_discovery` task publishes one statistic,
`sel(p, S) = #S`, which grades `u`, and asks for its partner.
The e-composition `eta(p)` is read off the object rather than submitted, so it
grades the target by a partition and is not part of the answer.

For partitions `gamma` and `lambda` with `n = |lambda|`, the target is the
elementary expansion, after the substitution `q = 1 + u`, of

```text
Delta_{m_gamma} Xi e_lambda = sum_eta c_eta(q, t) e_eta,
Xi F = M Delta_{e_1} Pi F[X/M],
M = (1-q)(1-t).
```

To distinguish the original `q`-coefficient from the shifted polynomial stored
by the benchmark, write

```text
c_eta^shift(u, t) := c_eta(1 + u, t).
```

This is Conjecture 13.2 of Iraci and Romero, which asks for exactly this
`tstat`. Note that the grading is in `u = q - 1`, not in `q` itself: Conjecture
13.1 there predicts that `Delta_F Xi G` becomes e-positive after `q -> 1 + u`
without specializing `t`, and every public target here lies in `N[u, t]`.

## Objects

Let `gamma |- m`. A **gamma-Dyck path of size n** is a parallelogram polyomino
of size `(m + n + 1) x n`: a pair of North/East lattice paths `(P, Q)` from
`(0,0)` to `(m + n + 1, n)` with the top path `P` strictly above the bottom
path `Q` except at the two endpoints, such that

- `Q` has no two consecutive North steps, and
- writing `alpha_i` for the number of East steps of `Q` in row `i`, the sequence
  `(alpha_1 - 1, alpha_2, ..., alpha_n)` rearranges to `gamma + 1^n`.

A **labeled** gamma-Dyck path assigns a positive integer to every North step of
`P`, strictly increasing along consecutive North steps. The word `w` of labels
read bottom to top has content `lambda`, meaning that the label `i` occurs
`lambda_i` times; these are the gamma-parking functions `PF^gamma_lambda`. For
`gamma` empty and `lambda = 1^n` they are the classical parking functions of
size `n`.

The polyomino has at least `(m + n + 1) + n - 1` cells and

```text
area(p) = (number of cells) - (m + 2n)
```

counts the surplus. The surplus cells are exactly those of each column lying
strictly above the minimal top path, so they form a canonical set `Area(p)`
with `#Area(p) = area(p)`. An object of this family is a pair `(p, S)` with
`S` a subset of `Area(p)`.

The canonical encoding is

```text
bottom|top|word|selected
```

where `bottom` and `top` are the comma-separated column heights of `Q` and `P`,
`word` is the comma-separated label word read bottom to top, and `selected`
lists the chosen cells as `column.row` in increasing order (empty for `S`
empty). The cell `column.row` occupies `[column - 1, column] x [row, row + 1]`.
For example

```text
0,0,0,1|1,2,2,2|1,2|2.1
```

is a `(1)`-Dyck path of size `2`, labeled `1, 2` bottom to top, with the single
cell of `Area(p)` selected.

The Python submission receives a `GammaParkingSelection` with:

- `selection.n` (the number of labels), `selection.width`, and
  `selection.size` (`= n + |gamma|`);
- `selection.gamma`, `selection.content`, and `selection.bottom_runs`;
- `selection.bottom`, `selection.top`, and `selection.word`;
- `selection.gaps` and `selection.ascents`;
- `selection.area_cells`, `selection.selected_cells`, `selection.selected`;
- `selection.area()`, `selection.selected_count()`, and `selection.eta()`.

## Public Statistic

The selection size is

```text
sel(p, S) = #S.
```

The same algorithm appears in `known_statistic.py`.

## e-Composition

The grading partition is Definition 2.7 of the source paper: let `P'` be the
path obtained from `P` by removing the first East step after the `i`-th North
step for every `i` not in `Asc(w)`; `eta(p)` is the multiset of lengths of the
maximal runs of consecutive North steps of `P'`. It is exposed as
`selection.eta()` and sorted into a partition.

## Public Data

`data/polynomials.json` contains `c_eta^shift(u, t)` for every pair `(gamma, lambda)`
with `1 <= |lambda| + |gamma| <= 5`. Terms have the form
`[eta, sel_exponent, partner_exponent, coefficient]`.

`data/q_equals_1.json` contains the `u = 1` specialization, the required
eta-graded distribution of the unknown statistic. `data/instances.json` lists
the objects for `|lambda| + |gamma| <= 4` and their public `sel` values.

**`data/instances.json` is a sample, not the scored set.** It lists 1,597 objects over 23 of the 46 scored fibers, while scoring runs over all 61,866 objects of the range in `data/polynomials.json`. Its `instances_max_*` field bounds that sample only. Enumerate the full scored range with `qtbench.combinatorics` before trusting a proposal.

## Submission

Submit a short, self-contained function

```python
def statistic(selection) -> int:
    ...
```

To score it:

```bash
uv run --frozen python scripts/evaluate/evaluate_scored_submission.py gpf path/to/submission.py
```

## Scoring

After the capability and source-economy screens, the evaluator enumerates every
public fiber once and compares the marginal and full eta-graded polynomial. Only
a complete numerical match proceeds to fresh-namespace shuffled replay and
the large-object resource gate. A pass is necessary but
not sufficient evidence of a genuine combinatorial statistic; see
`docs/checker.md`.

## References
- Alessandro Iraci and Marino Romero, "Delta and Theta operator expansions",
  arXiv:2203.10342, https://arxiv.org/abs/2203.10342. Defines gamma-Dyck paths, gamma-parking
  functions, `area`, the e-composition `eta`, and the operator `Xi`; Theorem 1.1
  proves the `t = 1` case, and Conjecture 13.2 poses this problem.
- Michele D'Adderio, "e-positivity of vertical strip LLT polynomials",
  arXiv:1906.02633, https://arxiv.org/abs/1906.02633. Proves the e-positivity used to settle the
  case `gamma = (k)`, `lambda = 1^n` of the `q -> 1 + u` conjecture that this
  target relies on.
- Jonah Blasiak, Mark Haiman, Jennifer Morse, Anna Pun, and George H. Seelinger,
  "A proof of the Extended Delta Conjecture",
  arXiv:2102.08815, https://arxiv.org/abs/2102.08815. The Extended Delta Theorem, whose `t = 1`
  monomial expansion is matched by these objects in Section 12.1 of the source
  paper.
- Michele D'Adderio, Alessandro Iraci, Yvan Le Borgne, Marino Romero, and Anna
  Vanden Wyngaerd, "Tiered trees and Theta operators",
  arXiv:2202.05706, https://arxiv.org/abs/2202.05706. The companion monomial-side model; Section
  12.3 of the source paper relates the two.
