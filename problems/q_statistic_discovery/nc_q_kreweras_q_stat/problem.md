# qtBench-Proposed q-Kreweras Natural-Statistic Challenge

## Task

This is a **qtBench-proposed natural-statistic challenge**, not an objectwise
open problem located in Reiner--Sommers or another primary source. Find a
statistic `statistic(partition)` on noncrossing partitions that returns a
**nonnegative integer** `krewstat(pi)` such that, for every `n >= 1` and every
partition `lambda` of `n`,

```text
Krew_lambda(q) = sum_{pi in NC(n), type(pi) = lambda} q^{krewstat(pi)},
```

where `Krew_lambda(q)` is the type A `q`-Kreweras number of Reiner and Sommers and
`type(pi)` is the multiset of block sizes of `pi`.

This `q_statistic_discovery` task has **no** public statistic. The single graded
exponent is the whole task, so `metadata.json` carries
`known_statistics: []` and there is no `known_statistic.py`. The fiber index,
the block type, is read from the object rather than submitted.

### Mathematical background

Kreweras' refinement of the Catalan numbers counts the noncrossing partitions of
`[n]` by block type:

```text
C_n = sum_{k} N(n, k),    N(n, k) = sum_{lambda |- n, l(lambda) = k} Krew(lambda),
Krew(lambda) = n! / ((n + 1 - l(lambda))! prod_j m_j(lambda)!),
```

with `m_j(lambda)` the multiplicity of `j` in `lambda`. Reiner and Sommers define
`q`-analogues of these numbers for every finite Weyl group, out of the Lusztig-Shoji
algorithm in Springer theory, and give closed formulas in every type. In type
`A_{n-1}` at the classical parameter `m = n + 1` their formula reads

```text
Krew_lambda(q) = q^{m(n - l(lambda)) - c(lambda)} (1 / [m]_q) [ m ; mu(lambda) ]_q,
c(lambda) = sum_j lambda'_j lambda'_{j+1},
```

with `mu(lambda)` the multiplicity vector and `lambda'` the conjugate partition.
Following Reiner--Sommers, when `|nu| <= m` the `q`-multinomial convention is

```text
[ m ; nu ]_q := [ m ; nu, m - |nu| ]_q
               = [m]_q! / ([m - |nu|]_q! prod_i [nu_i]_q!).
```

Thus the implicit leftover component for `mu(lambda)` is `m - l(lambda)`. These
polynomials lie in `N[q]`, specialize to the Kreweras numbers at `q = 1`, and sum
over `lambda` to the MacMahon `q`-Catalan number

```text
sum_{lambda |- n} Krew_lambda(q) = (1 / [n+1]_q) [ 2n ; n ]_q.
```

What Reiner and Sommers establish about them is a **cyclic sieving phenomenon**:
evaluated at roots of unity they count noncrossing partitions fixed by powers of the
rotation. That is an identity at finitely many points, not a statistic. We are not
aware of a rule assigning an exponent to each individual noncrossing partition.
Finding one is the benchmark-derived challenge posed here; the source establishes
the polynomials and cyclic sieving identities, not this objectwise-statistic request.

**Anchors the answer must satisfy**, all verified by the generator over the whole
public range:

```text
Krew_lambda(1) = Krew(lambda)                     the Kreweras number
sum_lambda Krew_lambda(q) = q-Catalan             the coarser grading is classical
krewstat = 0 on the all-singletons partition      Krew_{(1^n)}(q) = 1
krewstat = n(n-1) on the one-block partition      Krew_{(n)}(q) = q^{n(n-1)}
```

The second is the most useful one to a solver: summed over block types the target is
the MacMahon `q`-Catalan number, whose statistics on `NC(n)` are classical, so the
task is to find one that also splits correctly by type. The last two say that the
two extreme types pin the ends of the range.

## Objects

The benchmark **object** is a noncrossing partition of `[n]`: a set partition whose
blocks have pairwise disjoint convex hulls when `1, ..., n` are placed on a circle.
There are `C_n` of them. The fiber is the block type, read off the object.

This is the same object family as problem `1`, and the same Python class. The
submission receives a `NoncrossingPartition` with:

- `partition.n`, `partition.blocks`, `partition.block_type` (`= lambda`)
- `partition.block_count`, `partition.narayana_k`
- `partition.blocks_by_max`, `partition.block_maxima`, `partition.block_sizes_by_max`
- `partition.preceding_block_sizes`, `partition.nonmaximal_elements`
- `partition.area()`, the public statistic of problem `1`

`area` is exposed because it is the natural first guess and because it is public
already; it is **not** the answer here, and it is not a graded variable of this
target.

## Public Statistics

None. The single graded exponent belongs to the discovery task, so
`metadata.json` carries `known_statistics: []` and there is no
`known_statistic.py`. What is public instead is the list of identities above,
every one of which the generator verifies over the whole public range.

## Public Data

`data/polynomials.json` contains one case per size `n` with `1 <= n <= 11`, holding
`82499` noncrossing partitions in all across `194` block types. Each case lists its
`n` and terms

```json
[partition, q_exponent, coefficient]
```

so `Krew_lambda(q) = sum coefficient * q^{q_exponent}` over the terms with that
partition, with zero coefficients omitted. Every coefficient is positive and the
coefficients of one case total `C_n`.

`data/q_equals_1.json` contains the `q = 1` specialization: for each size the block
type distribution of `NC(n)`, that is the Kreweras numbers. Unlike the other
problems this marginal is **not a hint**: it is the ungraded count, which the fiber
realizes whatever the submitted statistic is. It is kept as a structural check on the
object model and on case identity, and it is checked from the same enumeration pass.

`data/instances.json` lists the public objects (`1 <= n <= 9`). It carries no
statistic values, because there are none to publish.

The targets are computed by the maintainer generator from the Reiner-Sommers closed
formula with exact integer polynomial arithmetic, every division checked to leave no
remainder.

The shipped data is cross-checked in `tests/problems/test_kreweras_problem.py`
against inputs the formula never sees: the block type distribution of the enumerated
`NC(n)`, Kreweras' own closed form for the counts, and the MacMahon `q`-Catalan
number recomputed from `q`-factorials for the sum over types.

**`data/instances.json` is a sample, not the scored set.** It lists 6,917 objects over 9 of the 11 scored fibers, while scoring runs over all 82,499 objects of the range in `data/polynomials.json`. Its `instances_max_*` field bounds that sample only. Enumerate the full scored range with `qtbench.combinatorics` before trusting a proposal.

## Submission

Submit a short, self-contained Python file defining:

```python
def statistic(partition) -> int:
    ...
```

The return value must be a nonnegative `int`. See `docs/checker.md` for the
admission checks; `examples/kreweras_area_submission.py` is a signature template
(`area`, right only at `n = 1`).

To score it:

```bash
uv run --frozen python scripts/evaluate/evaluate_scored_submission.py kreweras path/to/submission.py
```

## Scoring

After the capability and source-economy screens, the evaluator enumerates `NC(n)` once per
public size, groups the objects by block type and by the submitted exponent, and
checks the resulting coefficients against `data/polynomials.json`, together with the
`q = 1` block type marginal. A mismatch stops the evaluation. Only a complete match
proceeds to the fresh-namespace shuffled replay and large
adversarial objects under CPU and memory limits. Every stage must pass, though a
pass is necessary but not sufficient for a genuine statistic (see `docs/checker.md`).

As with problems `17` and `22` the resource gate is not the decisive lever: the
target has a closed formula, so it is cheap at any size. What the gate still rules
out is enumerating the fiber, which the ranking cheat needs and which is exponential.
Judge a proposal on whether it expresses a combinatorial idea.

## References
- Victor Reiner and Eric Sommers, "Weyl group `q`-Kreweras numbers and cyclic
  sieving", Annals of Combinatorics 22 (2018), 819-874,
  arXiv:1605.09172, https://arxiv.org/abs/1605.09172. Defines the `q`-Kreweras numbers for every finite
  Weyl group, gives the type A closed formula used here (Theorem 1.5), and proves the
  cyclic sieving phenomena they satisfy.
- Germain Kreweras, "Sur les partitions non croisees d'un cycle", Discrete
  Mathematics 1 (1972), 333-350,
  https://doi.org/10.1016/0012-365X(72)90041-6. The noncrossing partitions and the
  numbers `Krew(lambda)` counting them by block type.
- Victor Reiner, Dennis Stanton, and Dennis White, "The cyclic sieving phenomenon",
  Journal of Combinatorial Theory Series A 108 (2004), 17-50,
  https://doi.org/10.1016/j.jcta.2004.04.009. The phenomenon, and the `q`-Catalan
  instance on `NC(n)` that these numbers refine.
- Drew Armstrong, "Generalized noncrossing partitions and combinatorics of Coxeter
  groups", Memoirs of the American Mathematical Society 202 (2009),
  arXiv:math/0611106, https://arxiv.org/abs/math/0611106. The `NC^{(s)}(W)` lattices and the cyclic
  action the sieving refers to.
