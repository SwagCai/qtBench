# Rooted Tiered Tree Theta-Operator inv Partner

## Task

Find a statistic `statistic(tree)` on standard rooted tiered trees such that

```text
sum_T q^inv(T) t^statistic(T)
```

equals `G_mu(q, t)` for every tested partition `mu`.

This `t_statistic_discovery` task publishes one statistic, `inv`, and asks for
its partner.

For `n = |mu|`, the target is

```text
G_mu(q, t) = < Theta_{e_mu} e_1 , e_{1^{n+1}} >,
Theta_f F = Pi ( f[X/M] * Pi^{-1} F ),
M = (1-q)(1-t).
```

The first identity of Problem 6.5 of the tiered-tree paper asks for a statistic
`tstat` satisfying

```text
Theta_{e_{lambda(alpha)}} e_1
  = sum_{T in RTT(alpha)} q^inv(T) t^tstat(T) x^T.
```

Pairing with `e_{1^{n+1}}` restricts the identity to standard labellings of all
`n + 1` vertices. Its `t = 1` specialization is Theorem 4.6 there, a theorem
rather than a conjecture, and gives the `q`-enumerator of `inv`. The distinct
`q = 1` specialization is the required `t`-marginal of the unknown statistic.
Public fibers use partitions `mu`, the canonical representatives of the tier-size
compositions.

## Objects

A tiered tree has a level and a positive label on each vertex. An edge may join
two vertices only when their labels and levels increase in the same direction.

A rooted `alpha`-tree has one extra vertex, the root, alone at level `0`, with
`alpha_i` of the remaining vertices at level `i`. A standard object labels all
`n + 1` vertices bijectively with `1, ..., n + 1`, and `stRTT(mu)` is the set of
those.

The root is **not** exempt from the compatibility relation: its level is `0`, so
it is compatible exactly with the labels above its own. This is what
distinguishes this family from the zero-rooted family `RTT_0(mu)` of problem
`9`, where the root carries the extra label `0` and is compatible with
everything. The two families have different sizes: `|stRTT(1,1)| = 5` against
`|RTT_0(1,1)| = 4`, and `|stRTT(1,1,1)| = 60` against `|RTT_0(1,1,1)| = 39`.

The encoding stores both vectors over the labels `1, ..., n + 1`:

```text
levels_of_1_through_n_plus_1|parents_of_1_through_n_plus_1
```

The root is the unique vertex of level `0` and the unique vertex whose parent
entry is `0`. For example the unique `mu = (1)` object is

```text
0,1|0,1
```

The Python submission receives a `RootedTieredTree` with:

- `tree.n` (`= |mu|`), `tree.size` (`= n`), and `tree.vertex_count` (`= n+1`);
- `tree.root`, `tree.levels`, `tree.parents`, and `tree.tiers`;
- `tree.children`, `tree.ancestors`, and `tree.height`;
- `tree.compatible(i, j)` and `tree.inv()`.

## Public Statistic

The inversion number is

```text
inv(T) = #{(i,j): i, j non-root, j is a descendant of i,
                    j is compatible with p(i), and j < i}.
```

The same algorithm appears in `known_statistic.py`.

## Public Data

`data/polynomials.json` contains `G_mu(q,t)` for every partition `mu` with
`1 <= |mu| <= 5`. Terms have the form
`[inv_exponent, partner_exponent, coefficient]`.

`data/q_equals_1.json` contains the required marginal distribution of the
unknown statistic. `data/instances.json` lists the objects for `|mu| <= 4` and
their public `inv` values.

**`data/instances.json` is a sample, not the scored set.** It lists 2,042 objects over 11 of the 18 scored fibers, while scoring runs over all 75,088 objects of the range in `data/polynomials.json`. Its `instances_max_*` field bounds that sample only. Enumerate the full scored range with `qtbench.combinatorics` before trusting a proposal.

## Submission

Submit a short, self-contained function

```python
def statistic(tree) -> int:
    ...
```

To score it:

```bash
uv run --frozen python scripts/evaluate/evaluate_scored_submission.py rtt path/to/submission.py
```

## Scoring

After the capability and source-economy screens, the evaluator enumerates every
public fiber once and compares the marginal and full polynomial. Only a complete
numerical match proceeds to fresh-namespace shuffled replay, the integer-value
audit, and the large-object resource gate. A pass is necessary but not sufficient
evidence of a genuine combinatorial statistic; see `docs/checker.md`.

## References
- Michele D'Adderio, Alessandro Iraci, Yvan Le Borgne, Marino Romero, and Anna
  Vanden Wyngaerd, "Tiered trees and Theta operators",
  arXiv:2202.05706, https://arxiv.org/abs/2202.05706. Defines `RTT(alpha)` and `inv`, states the
  Theta Conjecture, proves the Hilbert series identity in Theorem 4.6, and poses
  the two identities in Problem 6.5; this problem is the first of them.
- William Dugan, Sam Glennon, Paul E. Gunnells, and Einar Steingrimsson,
  "Tiered trees, weights, and q-Eulerian numbers",
  arXiv:1702.02446, https://arxiv.org/abs/1702.02446. Introduces tiered trees.
- Biswadeep Bagchi and Srinibas Swain, "Tiered tree, Parking function and
  Postnikov-Shapiro algebra", arXiv:2408.03087, https://arxiv.org/abs/2408.03087. Relates tiered
  trees to graphical parking functions and parallelogram polyominoes.
- Alessandro Iraci and Marino Romero, "Delta and Theta operator expansions",
  arXiv:2203.10342, https://arxiv.org/abs/2203.10342. Section 12.3 discusses the relation between
  the tiered-tree monomial expansion and the elementary expansion of problems
  `18` and `20`.
