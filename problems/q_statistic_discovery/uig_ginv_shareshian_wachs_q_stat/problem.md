# Shareshian-Wachs Chromatic e-Positivity Composition Witness

## Task

Find a composition-valued witness `statistic(graph_permutation)` on Dyck graphs paired with their
`G`-nondescent permutations that returns a **composition of `n`** and, together
with the public `ginv` statistic, realizes the elementary-basis expansion of the
chromatic quasisymmetric function of Shareshian and Wachs:

```text
chi_G[X; q] = sum_{sigma in D_G^0} q^{ginv_G(sigma)} e_{lambda(theta(sigma))}
            = sum_{lambda |- n} c_lambda(q) e_lambda,
```

for every Dyck graph `G = ([n], E)`. Here `theta(sigma)` is the composition your
statistic returns and `lambda(theta(sigma))` is its underlying partition (the
checker sorts it), so only the multiset of parts matters. The public target for
each graph is the collection `{ c_lambda(q) }` of elementary coefficients.

Here `q_statistic_discovery` means q-graded witness discovery. The q-exponent
`ginv` is already public; the unknown `theta` is a **composition-valued witness**
whose underlying partition supplies the elementary-basis index.

### Mathematical background

This is a reformulation of the **Shareshian-Wachs conjecture**, that `chi_G` is
`e`-positive (`c_lambda(q) in N[q]`) for every natural unit interval graph. It
refines, and implies, the **Stanley-Stembridge conjecture** that Stanley's
chromatic symmetric function `chi_G[X; 1]` is `e`-positive (recently proved by
Hikita, 2024). A composition-valued statistic `theta` as above is exactly a
combinatorial witness of the `q`-refined `e`-positivity: grouping the objects by
`lambda(theta(sigma))` and reading off `ginv` must reproduce each `c_lambda(q)`.
No such `theta` is known in general, so this is an open problem.

What is being asked for here is stronger than positivity. Hikita (2024) settles
Stanley-Stembridge at `q = 1` by giving a probabilistic interpretation of the
numerical elementary coefficients for each real `q > 0`. The construction uses
rational `q`-weights rather than an assignment on the objects, so it neither
proves coefficientwise positivity in `N[q]` nor produces a candidate `theta`.
The objectwise witness requested here would establish both.

The chromatic quasisymmetric function is

```text
chi_G[X; q] = sum_{kappa proper} q^{asc_G(kappa)} x_kappa,
```

the sum over proper colorings `kappa : [n] -> Z_{>0}` (adjacent vertices get
different colors), with `x_kappa = prod_v x_{kappa(v)}` and
`asc_G(kappa) = #{ (i, j) in E : i < j, kappa(i) < kappa(j) }`. For a natural
unit interval graph this is a symmetric function, so its `e`-expansion exists;
each coefficient satisfies the reciprocity
`q^{|E|} c_lambda(1/q) = c_lambda(q)`, so its support is symmetric about
`|E| / 2` (its actual degree can be smaller than `|E|`). Two closed examples:
`chi_{K_n} = [n]_q! e_n`, and for `G = ([4], {(1,2),(2,3),(2,4),(3,4)})`,

```text
chi_G = (q^3 + 2q^2 + q) e_{(3,1)} + (q^4 + 2q^3 + 2q^2 + 2q + 1) e_{(4)}.
```

The target `c_lambda(q)` is computed directly from `chi_G` (proper colorings and
a change of basis), independently of any conjecture; the discovery of `theta` is
the open part.

## Objects

A **Dyck graph** (natural unit interval graph) `G = ([n], E)` has edge set
`E subseteq { (i, j) : 1 <= i < j <= n }` closed under "nesting to the diagonal":
if `(i, j) in E` then `(k, j) in E` for `i <= k < j` and `(i, h) in E` for
`i < h <= j`. Equivalently `G` is described by its weakly increasing
right-endpoint vector `b = (b_1, ..., b_n)` with `i <= b_i <= n`, where `(i, j)`
with `i < j` is an edge exactly when `j <= b_i`. There are `C_n` (Catalan) Dyck
graphs on `[n]`, one per Dyck path of size `n`.

For a permutation `sigma = sigma_1 ... sigma_n` in one-line notation set

```text
DesTilde_G(sigma) = { i in [n-1] : sigma_i > sigma_{i+1} and (sigma_{i+1}, sigma_i) not in E },
D_G^0            = { sigma in S_n : DesTilde_G(sigma) = empty }.
```

The benchmark **object** is a pair `(G, sigma)` with `sigma in D_G^0`. It is
encoded as the string `b + "|" + perm`, the comma-separated right-endpoint vector
followed by the comma-separated one-line notation of `sigma`. For example the
paper's graph with the identity permutation is

```text
2,4,4,4|1,2,3,4
```

and the single `n = 1` object is `1|1`. The total number of size-`n` objects
(summed over all Dyck graphs) is the odd double factorial `(2n-1)!!`.

The Python submission receives a `UnitIntervalGraphPermutation` object with:

- `graph_permutation.n`, `graph_permutation.size` (`= n`)
- `graph_permutation.b` (the right-endpoint vector of `G`)
- `graph_permutation.perm` (one-line notation `(sigma_1, ..., sigma_n)`)
- `graph_permutation.edges` (the edge set as pairs `(i, j)` with `i < j`)
- `graph_permutation.ginv()` (the public statistic)

For adjacency on large objects prefer the `O(n)` vector `b` over materializing
`edges`: vertices `u < v` are adjacent exactly when `v <= b[u - 1]`. The `edges`
set is a convenience for small graphs (it has `|E|` elements, which is quadratic
for dense graphs).

## Public Statistic

The public first statistic is the `G`-inversion number

```text
ginv(G, sigma) = invTilde_G(sigma) = #{ (i, j) : i < j, sigma_i > sigma_j, (sigma_j, sigma_i) in E },
```

the number of inversions of `sigma` whose two values are adjacent in `G`. It is
the `q`-grading of the target above. The same algorithm is implemented in
`known_statistic.py` and exposed as `graph_permutation.ginv()`.

## Public Data

`data/polynomials.json` contains, for every Dyck graph on `[n]` with
`1 <= n <= 7` (all `C_1 + ... + C_7 = 625` graphs), the elementary coefficients
of `chi_G`. Each case lists its right-endpoint vector `b` and terms
`[partition, ginv_exponent, coefficient]`, so the partition-graded `q`-polynomial
`c_lambda(q)` is `sum_{ginv} coefficient * q^{ginv}` over the terms with that
partition. The coefficients are nonnegative (`e`-positivity), each `c_lambda(q)`
satisfies `q^{|E|} c_lambda(1/q) = c_lambda(q)`, and their total is `|D_G^0|`;
equivalently,
`sum_lambda c_lambda(q)` equals the `ginv` generating function
`sum_{sigma in D_G^0} q^{ginv_G(sigma)}` (an independent cross-check of the target
against the object model and the public statistic).

`data/q_equals_1.json` contains the `q = 1` specialization: for each graph the
partition-multiset `{ (lambda, c_lambda(1)) }`. This is the elementary expansion
of Stanley's ordinary chromatic symmetric function `chi_G[X; 1]` and is the
required necessary distribution of `lambda(theta(sigma))` for the unknown
`theta` (a necessary, not sufficient, condition).

`data/instances.json` lists the public objects (`1 <= n <= 6`) with their `ginv`
values. It does not contain the target `theta` statistic.

**`data/instances.json` is a sample, not the scored set.** It lists 11,464 objects over 196 of the 625 scored fibers, while scoring runs over all 146,599 objects of the range in `data/polynomials.json`. Its `instances_max_*` field bounds that sample only. Enumerate the full scored range with `qtbench.combinatorics` before trusting a proposal.

## Submission

Submit a short, self-contained Python file defining:

```python
def statistic(graph_permutation) -> tuple[int, ...]:
    ...
```

The return value must be a **composition of `n`**: a tuple (or list) of positive
integers summing to `graph_permutation.n`. Only its underlying partition matters.
See `docs/checker.md` for the admission checks; `examples/uig_ltr_maxima_submission.py`
is a signature template (the paper's left-to-right `G`-maxima guess, correct only
for a subclass of graphs).

To score it:

```bash
uv run --frozen python scripts/evaluate/evaluate_scored_submission.py uig path/to/submission.py
```

## Scoring

After the capability and source-economy screens, the evaluator enumerates every public
`(G, sigma)` object once, groups them by the submitted partition
`lambda(theta(sigma))` and by `ginv`, and checks the resulting partition-graded
coefficients against `data/polynomials.json`, together with the `q = 1`
partition-multiset marginal. A mismatch stops the evaluation. Only a complete
match proceeds to fresh-namespace shuffled replay, the integer-value audit, and
large adversarial objects under CPU and memory limits. Every stage must pass,
though a pass is necessary but not sufficient for a genuine statistic (see
`docs/checker.md`).

For this problem, the defining proper-colouring expansion gives a formula for
`chi_G`; the open conjecture is its coefficientwise `e`-positivity, and this task
asks more specifically for an objectwise witness `theta`. No general scalable
local rule for those `e`-coefficients or for `theta` is known. The resource gate
therefore targets submissions that globally reconstruct and redistribute the
`e`-basis target on each probe, while a genuine `theta` should be a fast function
of a single object.

## References
- John Shareshian and Michelle L. Wachs, "Chromatic quasisymmetric functions",
  Advances in Mathematics 295 (2016), 497-551, arXiv:1405.4629, https://arxiv.org/abs/1405.4629.
  Introduces `chi_G[X; q]`, proves its symmetry for natural unit interval graphs,
  and states the `e`-positivity (and `e`-unimodality) conjecture reformulated here.
- Richard P. Stanley and John R. Stembridge, "On immanants of Jacobi-Trudi
  matrices and permutations with restricted position", Journal of Combinatorial
  Theory Series A 62 (1993), 261-279,
  https://doi.org/10.1016/0097-3165(93)90048-D. The original
  `(3+1)`-free `e`-positivity conjecture that the Shareshian-Wachs conjecture
  refines and, together with the reduction below, implies.
- Mathieu Guay-Paquet, "A modular relation for the chromatic symmetric functions
  of (3+1)-free posets", arXiv:1306.2400, https://arxiv.org/abs/1306.2400.
  Reduces the Stanley-Stembridge conjecture for all `(3+1)`-free posets to unit
  interval orders, which is what makes the Shareshian-Wachs conjecture -- stated
  for natural unit interval graphs -- imply it rather than only refine it on a
  subclass.
- Tatsuyuki Hikita, "A proof of the Stanley-Stembridge conjecture",
  arXiv:2410.12758 (2024), https://arxiv.org/abs/2410.12758. Gives a
  probabilistic interpretation of the numerical elementary coefficients of the
  chromatic quasisymmetric function of any unit interval graph for real `q > 0`,
  and derives the `q = 1` Stanley-Stembridge conjecture as a corollary. Its
  rational `q`-weights do not prove coefficientwise positivity in `N[q]` and do
  not give a rule sending each `(G, sigma)` to a composition, so the refined
  conjecture and the stronger problem posed here remain open.
- Christos A. Athanasiadis, "Power sum expansion of chromatic quasisymmetric
  functions", Electronic Journal of Combinatorics 22 (2015), no. 2, #P2.7,
  arXiv:1409.2595, https://arxiv.org/abs/1409.2595. Proves the Shareshian-Wachs power-sum formula,
  a proven expansion of `chi_G[X; q]` in another basis.
