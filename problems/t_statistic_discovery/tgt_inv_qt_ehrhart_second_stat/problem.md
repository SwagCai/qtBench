# Threshold Graph Spanning Tree Flow-Polytope Ehrhart inv Partner

## Task

Find a statistic `statistic(tree)` on spanning trees of connected threshold
graphs such that

```text
sum_{T in T(G)} q^inv(T) t^statistic(T)
```

equals `E_G(q, t)` for every tested connected threshold graph `G`.

This `t_statistic_discovery` task publishes one statistic, `inv`, and asks for
its partner.

For a connected threshold graph `G` on `{0, 1, ..., n}`, the target is the
`(q,t)`-weighted Ehrhart function of the flow polytope of `G` with netflow
`(-n, 1, ..., 1)`:

```text
E_G(q, t) = Ehr_{q,t}(F_G(-n, 1, ..., 1))
          = sum_{A in F_G cap Z^E} wt_{q,t}(A),
wt_{q,t}(A) = (-(1-t)(1-q))^{#{a_ij > 0} - n} * prod_{i,j} wt_{q,t}(a_ij),
wt_{q,t}(b) = (q^b - t^b)/(q - t) for b > 0, and 1 for b = 0.
```

Liu, Meszaros and Morales prove that its `t = 1` specialization is the `inv`
enumerator of the spanning trees of `G`, and conjecture that `E_G(q, t)` lies in
`N[q, t]`. Section 6.1 of their paper asks for exactly the statistic above and
records that they were unable to find one. The conjecture is still listed as
open, verified to `n = 9`.

Two features make this a strong target. The `t = 1` marginal is a **theorem**,
not a conjecture, so the `q = 1` marginal of every public target is a genuine
constraint on the answer. And the statistic **must depend on the graph** and not
only on the labelled tree: Example 6.5 there exhibits a threshold graph whose
Mobius refinement over the subgraph poset is not `q,t`-positive, which rules out
any `stat(T)` that ignores `G`. The graph is therefore part of the object, not
merely the fiber key.

For `G = K_{n+1}` the target is the bigraded Hilbert series of the space of
diagonal harmonics `DH_n` (Haglund; Carlsson--Mellit), so this problem contains
the classical tree model for diagonal harmonics as its densest fiber.

## Objects

A **threshold graph** is built from a single vertex by repeatedly adding either
a dominating vertex or an isolated one. Labelled by reverse degree sequence on
`{0, 1, ..., n}`, it satisfies the staircase property: if `i` and `j` are
adjacent then so are `i'` and `j'` for every `i' <= i`, `j' <= j` with
`i' != j'`. A connected one is therefore determined by its **up-degrees** `u`,
where vertex `i` is adjacent to `j > i` exactly when `j <= i + u_i`, and

```text
u_0 = n > u_1 > ... > u_{k-1} >= 1,    u_i = 0 for i >= k.
```

There are `2^(n-1)` of them on `n + 1` vertices, one for each subset of
`{1, ..., n-1}`; `u = (n, n-1, ..., 1)` is the complete graph `K_{n+1}` and
`u = (n, 0, ..., 0)` is the star. Vertex `0` always dominates.

An object is a spanning tree `T` of such a graph, rooted at `0`. The encoding
records the graph and the parent of each vertex `1, ..., n`:

```text
up_degrees|parents
```

For example

```text
3,2,1|0,0,0
```

is the star-shaped spanning tree of `K_4`, and `3,0,0|0,0,0` is the only
spanning tree of the star on four vertices.

The Python submission receives a `ThresholdSpanningTree` with:

- `tree.n`, `tree.size` (`= n`), and `tree.vertex_count` (`= n+1`);
- `tree.root` (`= 0`), `tree.up_degrees`, `tree.parents`, and `tree.degrees`;
- `tree.adjacent(i, j)`, `tree.neighbours(i)`, and `tree.edges`;
- `tree.children`, `tree.ancestors(v)`, `tree.height`, `tree.subtree_sizes`;
- `tree.is_increasing()` and `tree.inv()`.

The graph side is computed lazily, so `adjacent` is constant time and `degrees`
is linear; only `edges` materializes the (quadratic) edge set.

## Public Statistic

The inversion number is

```text
inv(T) = #{(i,j): i > j, j is a descendant of i in T},
```

equivalently the number of pairs (vertex, strictly larger ancestor). For a
threshold graph every inversion is a `kappa`-inversion, so `inv` is also
Gessel's inversion enumerator statistic and `sum_T q^inv(T) = t_G(1, q)`.

The same algorithm appears in `known_statistic.py`.

## Public Data

`data/polynomials.json` contains `E_G(q,t)` for every connected threshold graph
with `1 <= n <= 6`, that is all `63` of them. Terms have the form
`[inv_exponent, partner_exponent, coefficient]`.

`data/q_equals_1.json` contains the required marginal distribution of the
unknown statistic. `data/instances.json` lists the objects for `n <= 5` and
their public `inv` values.

**`data/instances.json` is a sample, not the scored set.** It lists 4,257 objects over 31 of the 63 scored fibers, while scoring runs over all 71,585 objects of the range in `data/polynomials.json`. Its `instances_max_*` field bounds that sample only. Enumerate the full scored range with `qtbench.combinatorics` before trusting a proposal.

## Submission

Submit a short, self-contained function

```python
def statistic(tree) -> int:
    ...
```

To score it:

```bash
uv run --frozen python scripts/evaluate/evaluate_scored_submission.py tgt path/to/submission.py
```

## Scoring

After the capability and source-economy screens, the evaluator enumerates every
public fiber once and compares the marginal and full polynomial. Only a complete
numerical match proceeds to fresh-namespace shuffled replay, the integer-value
audit, and the large-object resource gate. A pass is necessary but not sufficient
evidence of a genuine combinatorial statistic; see `docs/checker.md`.

## References
- Ricky Ini Liu, Karola Meszaros, and Alejandro H. Morales, "Flow polytopes and
  the space of diagonal harmonics", arXiv:1610.08370, https://arxiv.org/abs/1610.08370 (Canad. J.
  Math., 2019). Defines the `(q,t)`-Ehrhart function (Definition 2.1, Remark
  2.2) and threshold graphs (Definition 2.4), proves the `t = 1` spanning-tree
  formula (Theorem 3.8), states the positivity Conjecture 6.1, and poses this
  statistic in Section 6.1.
- Alejandro H. Morales, "Conjectures",
  https://sites.google.com/view/ahmorales/research/conjectures. Lists
  Conjecture 6.1 as open, verified to `n = 9`.
- James Haglund, "A polynomial expression for the Hilbert series of the
  quotient ring of diagonal coinvariants", Adv. Math. 227 (2011), 2092-2106.
  The Tesler-matrix formula that identifies the complete-graph fiber with the
  diagonal harmonics Hilbert series.
- Erik Carlsson and Anton Mellit, "A proof of the shuffle conjecture",
  arXiv:1508.06239, https://arxiv.org/abs/1508.06239. Proves the Haglund--Loehr Hilbert series
  formula that the complete-graph fiber specializes.
- Ira M. Gessel, "Enumerative applications of a decomposition for graphs and
  digraphs", Discrete Math. 139 (1995), 257-271. Introduces `kappa`-inversions
  and proves `I_G(q) = t_G(1, q)`, the `t = 1` side of the target.
