# Doubly Decorated Dyck Path Unified-Delta Area Partner

## Task

Find a statistic `statistic(path)` on standardly labelled doubly decorated Dyck
paths such that the joint distribution

```text
sum_D q^area(D) t^statistic(D)
```

matches the target polynomial `F_{n,k,l}(q, t)` for every tested triple
`(n, k, l)`.

This `t_statistic_discovery` task publishes one statistic, the decorated `area`,
and asks for its `t`-partner.

The target is the "Hilbert series" of the unified-Delta symmetric function of
Iraci, Nadeau and Vanden Wyngaerd,

```text
F_{n,k,l}(q, t) = < Theta_{e_k} Theta_{e_l} nabla e_{n-k-l} , e_{1^n} >,
```

where `Theta_f` is the Theta operator of D'Adderio, Iraci and Vanden Wyngaerd and
`nabla` is the Bergeron-Garsia operator. The pairing with `e_{1^n} = h_{1^n}`
restricts the symmetric function to the standardly labelled objects `LD(n)^{*k, •l}`.
Their conjecture for a **unified Delta conjecture** asks for a statistic `qstat`
on all labelled doubly decorated Dyck paths `LD(n)^{*k, •l}` realizing the full
symmetric-function identity

```text
Theta_{e_k} Theta_{e_l} nabla e_{n-k-l} = sum_{D in LD(n)^{*k,•l}} q^qstat(D) t^area(D) x^D;
```

restricting to standard labellings gives exactly the scalar `q,t`-target above.
They conjecture (with significant computational evidence) the identity at
`q = 1`,

```text
Theta_{e_k} Theta_{e_l} nabla e_{n-k-l} |_{q=1} = sum_{D in LD(n)^{*k,•l}} t^area(D) x^D,
```

so setting `q = 1` is conjectured to recover `sum_D t^area(D)`. Their proved
partial result is instead the different specialization at `t = 0`, where they
construct a `q`-statistic on the area-zero objects. The full `q,t` statistic
remains open. When `l = 0` or `k = 0` the target specializes to the (rise, resp.
valley) Delta conjecture, whose rise version is a theorem.

### A note on nomenclature

The source paper phrases the open problem as finding a **`q`-statistic** paired
with `area` (there the exponent of `t`). This benchmark uses the opposite
convention: `area` is the public **`q`-statistic** and the sought partner is the
**`t`-statistic**. The relabelling is harmless because `F_{n,k,l}` is
`q,t`-symmetric, so this is a `t`-statistic discovery problem: the `q = 1`
marginal (the required distribution of the unknown partner) equals the `area`
distribution.

## Objects

A **Dyck path** of size `n` is a lattice path from `(0, 0)` to `(n, n)` using unit
North and East steps and staying weakly above the diagonal `x = y`. A **labelled**
Dyck path carries a positive-integer label on each North (vertical) step, strictly
increasing along each maximal run of consecutive vertical steps (bottom to top). A
**standard labelling** uses each of `1, ..., n` exactly once.

- a **rise** is a vertical step preceded by another vertical step;
- a **valley** is a vertical step preceded by a horizontal step; a valley (the
  `i`-th vertical step, with `e` horizontal steps immediately before it) is
  **contractible** when `e >= 2`, or when `e == 1` and the label of the
  `(i-1)`-th vertical step is strictly smaller than that of the `i`-th.

A **doubly decorated** labelled Dyck path additionally distinguishes `k` decorated
rises and `l` decorated contractible valleys. `LD(n)^{*k, •l}` is the set of
standardly labelled size-`n` such objects with `k` decorated rises and `l`
decorated valleys; it is nonempty exactly when `k, l >= 0` and `k + l <= n - 1`.

The **area word** `a` has `a_i = y - x` when the `i`-th vertical step is taken (the
number of whole cells in row `i` between the path and the diagonal). An object is
encoded as the string `path + "|" + labels + "|" + drise + "|" + dvalley`, where
`path` is the North/East word, `labels` lists the label of each vertical step in
step order, and `drise`/`dvalley` are the comma-separated 1-indexed vertical-step
positions of the decorated rises and valleys (either may be empty). For example
the single-step `n = 1` path is

```text
NE|1||
```

The Python submission receives a `DecoratedLabelledDyckPath` object with:

- `path.n`, `path.size` (`= n`), `path.k`, `path.l`
- `path.path` (the North/East word)
- `path.labels` (label of each vertical step in step order)
- `path.area_word` (the area word `a`)
- `path.rises`, `path.valleys`, `path.contractible_valleys` (1-indexed positions)
- `path.decorated_rises`, `path.decorated_valleys` (the decorated positions)
- `path.area()`

## Public Statistic

The decorated `area` sums the area-word letters off the decorated rises:

```text
area(D) = sum of a_i over vertical steps i that are NOT decorated rises.
```

The same algorithm is implemented in `known_statistic.py`.

## Public Data

`data/polynomials.json` contains the target `F_{n,k,l}(q, t)` for every fiber with
`1 <= n <= 6` (all `k, l >= 0` with `k + l <= n - 1`); each term is
`[area_exponent, partner_exponent, coefficient]`. The polynomials are
`q,t`-symmetric and total `|LD(n)^{*k, •l}|`. They are the unified-Delta Hilbert
series above, computed in the public oracle and independently checked to
reproduce the `area` distribution of `LD(n)^{*k, •l}` at `t = 1`.

`data/q_equals_1.json` contains the `q = 1` specialization, the required
one-variable distribution of the unknown partner statistic (a necessary, not
sufficient, condition).

`data/instances.json` lists the public objects (`1 <= n <= 5`) with their `area`
values. It does not contain the target `t`-statistic.

**`data/instances.json` is a sample, not the scored set.** It lists 11,189 objects over 35 of the 56 scored fibers, while scoring runs over all 244,346 objects of the range in `data/polynomials.json`. Its `instances_max_*` field bounds that sample only. Enumerate the full scored range with `qtbench.combinatorics` before trusting a proposal.

## Submission

Submit a short, self-contained Python file defining:

```python
def statistic(path) -> int:
    ...
```

The return value must be a nonnegative integer. See `docs/checker.md` for the
admission checks.

To score it:

```bash
uv run --frozen python scripts/evaluate/evaluate_scored_submission.py ddyck path/to/submission.py
```

## Scoring

After the capability and source-economy screens, the evaluator enumerates each
public `LD(n)^{*k, •l}` fiber once. From the same submitted values, it checks the
explicit `q = 1` marginal and every `q,t` coefficient. Only a complete match
proceeds to fresh-namespace shuffled replay and large
adversarial paths under CPU and memory limits. A mismatch stops the evaluation,
and passing `q = 1` alone is insufficient. Every stage must pass, though a pass
is necessary but not sufficient for a genuine statistic (see `docs/checker.md`).

## References
- Alessandro Iraci, Philippe Nadeau, and Anna Vanden Wyngaerd, "Smirnov words and
  the Delta Conjectures", arXiv:2312.03956, https://arxiv.org/abs/2312.03956.
  Conjectures the target identity at `q = 1` (with significant computational
  evidence), proves the distinct `t = 0` case, and poses the open problem of the
  full `q,t` statistic on `LD(n)^{*k, •l}`.
- Michele D'Adderio, Alessandro Iraci, and Anna Vanden Wyngaerd, "Theta operators,
  refined Delta conjectures, and coinvariants", Advances in Mathematics 376
  (2021), 107447, arXiv:1906.02623, https://arxiv.org/abs/1906.02623. Introduces the Theta
  operators `Theta_f` and the `(2,2)` conjecture
  `Theta_{e_l} Theta_{e_k} nabla e_{n-k-l}`.
- Michele D'Adderio and Anton Mellit, "A proof of the compositional Delta
  conjecture", Advances in Mathematics 402 (2022), 108342,
  arXiv:2011.11467, https://arxiv.org/abs/2011.11467. Proves the rise Delta conjecture, i.e. the
  `l = 0` specialization of the target.
- Mike Zabrocki, "A module for the Delta conjecture", arXiv:1902.08966 (2019),
  https://arxiv.org/abs/1902.08966. The `(2,1)` bosonic-fermionic diagonal
  coinvariant module whose graded Frobenius characteristic is conjecturally this
  symmetric function; the origin of the coinvariant-ring motivation.
- James Haglund, Jeffrey B. Remmel, and Andrew T. Wilson, "The Delta Conjecture",
  Transactions of the American Mathematical Society 370 (2018), 4029-4057,
  https://doi.org/10.1090/tran/7096. The Delta conjecture
  `Delta'_{e_{n-k-1}} e_n = Theta_{e_k} nabla e_{n-k}` recovered at `l = 0`.
