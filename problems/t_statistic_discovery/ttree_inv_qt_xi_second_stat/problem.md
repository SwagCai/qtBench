# Zero-Rooted Tiered Tree Xi-Operator inv Partner

## Task

Find a statistic `statistic(tree)` on standard zero-rooted tiered trees such
that

```text
sum_T q^inv(T) t^statistic(T)
```

equals `F_mu(q, t)` for every tested partition `mu`.

This `t_statistic_discovery` task publishes one statistic, `inv`, and asks for
its partner.

For `n = |mu|`, the target is

```text
F_mu(q, t) = < Xi e_mu, e_{1^n} >,
Xi F = M Delta_{e_1} Pi F[X/M],
M = (1-q)(1-t).
```

The Symmetric Theta Conjecture and Problem 6.5 of the tiered-tree paper ask for
a statistic `tstat` satisfying

```text
Xi e_{lambda(alpha)}
  = sum_{T in RTT_0(alpha)} q^inv(T) t^tstat(T) x^T.
```

Pairing with `e_{1^n}` restricts the identity to standard non-root labels
`1, ..., n`. Public fibers use partitions `mu`, the canonical representatives
of the tier-size compositions.

## Objects

A tiered tree has a positive level and a positive label on each non-root
vertex. An edge may join two non-root vertices only when their labels and
levels increase in the same direction.

`RTT_0(alpha)` has one additional root whose label and level are both fixed at
`0`. The root is compatible with every non-root vertex. A standard object uses
each non-root label in `[n]` exactly once and has `alpha_i` vertices at level
`i`.

The root is fixed and therefore omitted from the encoding:

```text
levels_of_1_through_n|parents_of_1_through_n
```

A parent value of `0` denotes the root. For example, the unique `mu = (1)`
object is

```text
1|0
```

The Python submission receives a `ZeroRootedTieredTree` with:

- `tree.n`, `tree.size` (`= n`), and `tree.vertex_count` (`= n+1`);
- `tree.root` (`= 0`), `tree.levels`, `tree.parents`, and `tree.tiers`;
- `tree.children`, `tree.ancestors`, and `tree.height`;
- `tree.compatible(i, j)` and `tree.inv()`.

## Public Statistic

The inversion number is

```text
inv(T) = #{(i,j): i,j != 0, j is a descendant of i,
                    j is compatible with p(i), and j < i}.
```

The same algorithm appears in `known_statistic.py`.

## Public Data

`data/polynomials.json` contains `F_mu(q,t)` for every partition `mu` with
`1 <= |mu| <= 5`. Terms have the form
`[inv_exponent, partner_exponent, coefficient]`.

`data/q_equals_1.json` contains the required marginal distribution of the
unknown statistic. `data/instances.json` lists the objects for `|mu| <= 4` and
their public `inv` values.

**`data/instances.json` is a sample, not the scored set.** It lists 1,145 objects over 11 of the 18 scored fibers, while scoring runs over all 35,761 objects of the range in `data/polynomials.json`. Its `instances_max_*` field bounds that sample only. Enumerate the full scored range with `qtbench.combinatorics` before trusting a proposal.

## Submission

Submit a short, self-contained function

```python
def statistic(tree) -> int:
    ...
```

To score it:

```bash
uv run --frozen python scripts/evaluate/evaluate_scored_submission.py ttree path/to/submission.py
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
  arXiv:2202.05706, https://arxiv.org/abs/2202.05706. Defines `RTT_0(alpha)` and `inv`, states the
  Symmetric Theta Conjecture, and poses the two identities in Problem 6.5.
- Alessandro Iraci and Marino Romero, "Delta and Theta operator expansions",
  arXiv:2203.10342, https://arxiv.org/abs/2203.10342. Defines the Xi operator used in the target.
- William Dugan, Sam Glennon, Paul E. Gunnells, and Einar Steingrimsson,
  "Tiered trees, weights, and q-Eulerian numbers",
  arXiv:1702.02446, https://arxiv.org/abs/1702.02446. Introduces tiered trees.
