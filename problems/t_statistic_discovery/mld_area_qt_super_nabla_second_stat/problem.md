# Multi-Labelled Dyck Path Super-Nabla Area Partner

## Task

Find a statistic `statistic(path)` on standard multi-labelled `k^n` Dyck paths
such that the joint distribution

```text
sum_L q^area(L) t^statistic(L)
```

matches the target polynomial `H_{n,k}(q, t)` for every tested pair `(n, k)`.

This `t_statistic_discovery` task publishes one statistic, the rectangular
`area`, and asks for its `t`-partner.

The target is the "Hilbert series" of the super-nabla symmetric function of
Bergeron, Haglund, Iraci and Romero,

```text
H_{n,k}(q, t) = < nabla_*^k e_n , e_{1^n} (x) ... (x) e_{1^n} >   (k + 1 factors),
```

where the **super nabla** operator `nabla_*: Lambda -> Lambda (x) Lambda` is
defined on the modified Macdonald basis by `nabla_* Ht_mu = Ht_mu (x) Ht_mu`, so
that `nabla_*^k e_n` lives in `Lambda^{(x)(k+1)}`. Pairing each tensor factor with
`e_{1^n} = h_{1^n}` restricts the symmetric function to the objects whose `k + 1`
label rows are each a permutation of `[n]`. Their open problem asks for a
statistic `tstat` on all multi-labelled Dyck paths `LD_{k^n}` realizing the full
identity

```text
nabla_*^k e_n = sum_{(pi, w) in LD_{k^n}} q^area(pi) t^tstat(pi, w) XX^w;
```

restricting to standard labellings gives exactly the scalar `q,t`-target above.
Their theorem gives the identity at `t = 1`,

```text
nabla_*^k e_n |_{t=1} = sum_{L in LD_{k^n}} q^area(L) XX^L,
```

so setting `t = 1` recovers `sum_L q^area(L)`; the full `q,t` statistic remains
open, and the accompanying `m`-positivity conjecture is what predicts that such
a statistic exists. The source checks `n <= 6` and at most six tensor factors,
which in this statement's exponent convention means `n <= 6` and `k <= 5`,
because `nabla_*^k e_n` has `k + 1` factors. When the super-nabla parameter is
`k = 1`, suitable scalar products in the extra sets of variables recover
`nabla e_n` (the shuffle theorem) and, with an independent decoration index `r`,
the unprimed `Delta_{e_{n-r}} e_n` specialization of the valley Delta conjecture.
Here the source decorates `r` peaks, including the topmost peak, which has no
following valley; this is why the operator is `Delta_{e_{n-r}}`, rather than the
primed `Delta'_{e_{n-r-1}}`. A solution would extend both specializations.

## Objects

A `kn x n` **Dyck path** is a lattice path of `n` North and `kn` East unit steps
from `(0, 0)` to `(kn, n)` staying weakly above the main diagonal `ky = x`. With
`col(i)` the `x`-coordinate of the `i`-th North step this says `col(i) <= k(i-1)`.

A **multi-labelled** `k^n` Dyck path is a pair `(pi, w)` where `w = (w_1, ..., w_n)`
assigns a `(k+1)`-tuple `w_i = (w_{i,0}, ..., w_{i,k})` of positive integers to the
`i`-th North step, subject to

```text
#{ j : w_{i,j} >= w_{i+1,j} } <= col(i+1) - col(i)      for 1 <= i < n,
```

i.e. the number of weak descents at position `i`, counted across the `k + 1` label
rows, is at most the number of East steps between the `i`-th and `(i+1)`-th North
step. `LD_{k^n}` denotes this set. A labelling is **standard** when each row
`w_{*,j} = (w_{1,j}, ..., w_{n,j})` is a permutation of `[n]`; those are the objects
selected by the Hilbert-series pairing, and for them weak descents are strict.

An object is encoded as the string `path + "|" + row_0 + "|" + ... + "|" + row_k`,
where `path` is the North/East word and each `row_j` is the comma-separated `j`-th
label row. For example the `n = 2`, `k = 1` object on the staircase is

```text
NENE|2,1|1,2
```

The Python submission receives a `MultiLabelledDyckPath` object with:

- `path.n`, `path.size` (`= n`), `path.k`
- `path.path` (the North/East word)
- `path.rows` (the `k + 1` label rows), `path.labels` (the tuples `w_i`)
- `path.columns` (`col(i)`), `path.gaps` (`col(i+1) - col(i)`)
- `path.area_word`, `path.descents`
- `path.area()`

## Public Statistic

The `area` is the number of whole lattice cells between the path and the main
diagonal, and does not depend on the labels:

```text
area(pi) = sum_{i=1}^{n} ( k (i - 1) - col(i) ).
```

The same algorithm is implemented in `known_statistic.py`.

## Public Data

`data/polynomials.json` contains the target `H_{n,k}(q, t)` for every fiber with
`1 <= k <= 4` and `1 <= n <= max(3, 6 - k)` (15 fibers; the object count grows
very fast in both parameters); each term is
`[area_exponent, partner_exponent, coefficient]`. The polynomials are
`q,t`-symmetric and total the number of standard elements of `LD_{k^n}`. They are
the super-nabla Hilbert series above, computed in the public oracle and
independently checked to reproduce the `area` distribution of `LD_{k^n}` at
`t = 1`.

`data/q_equals_1.json` contains the `q = 1` specialization, the required
one-variable distribution of the unknown partner statistic (a necessary, not
sufficient, condition).

`data/instances.json` lists the public objects of every fiber with at most
`10000` of them, with their `area` values. It does not contain the target
`t`-statistic.

**`data/instances.json` is a sample, not the scored set.** It lists 8,181 objects over 12 of the 15 scored fibers, while scoring runs over all 172,481 objects of the range in `data/polynomials.json`. Its `instances_max_*` field bounds that sample only. Enumerate the full scored range with `qtbench.combinatorics` before trusting a proposal.

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
uv run --frozen python scripts/evaluate/evaluate_scored_submission.py mld path/to/submission.py
```

## Scoring

After the capability and source-economy screens, the evaluator enumerates each
public `LD_{k^n}` fiber once. From the same submitted values, it checks the
explicit `q = 1` marginal and every `q,t` coefficient. Only a complete match
proceeds to fresh-namespace shuffled replay and large
adversarial paths under CPU and memory limits. A mismatch stops the evaluation,
and passing `q = 1` alone is insufficient. Every stage must pass, though a pass
is necessary but not sufficient for a genuine statistic (see `docs/checker.md`).

## References
- Francois Bergeron, James Haglund, Alessandro Iraci, and Marino Romero, "The
  super nabla operator", arXiv:2303.00560, https://arxiv.org/abs/2303.00560.
  Defines `nabla_*` and multi-labelled Dyck paths, proves the `t = 1` monomial
  expansion, and poses the open problem of the `t`-statistic sought in this task.
- Erik Carlsson and Anton Mellit, "A proof of the shuffle conjecture", Journal of
  the American Mathematical Society 31 (2018), 661-697,
  arXiv:1508.06239, https://arxiv.org/abs/1508.06239. The `k = 1`, `<e_n, nabla_*> e_n = nabla e_n`
  specialization of the target.
- James Haglund, Jeffrey B. Remmel, and Andrew T. Wilson, "The Delta Conjecture",
  Transactions of the American Mathematical Society 370 (2018), 4029-4057,
  https://doi.org/10.1090/tran/7096. The valley Delta conjecture, recovered from
  the super-nabla `k = 1` case by pairing the extra labels with `e_{n-r} h_r`,
  where `r` counts decorated peaks including the topmost peak; the resulting
  operator is the unprimed `Delta_{e_{n-r}}`.
- Adriano M. Garsia and Mark Haiman, "A graded representation model for
  Macdonald's polynomials", Proceedings of the National Academy of Sciences 90
  (1993), 3607-3610, https://doi.org/10.1073/pnas.90.8.3607. The modified
  Macdonald polynomials `Ht_mu` on which `nabla_*` is diagonal.
- Houcine Ben Dali, "A formula for the Jack super nabla operator",
  arXiv:2509.18625, https://arxiv.org/abs/2509.18625. A Jack-deformed analogue of
  the operator, and further evidence for its positivity.
- Alessandro Iraci and Marino Romero, "Delta and Theta operator expansions",
  Forum of Mathematics Sigma 12 (2024), e30, arXiv:2203.10342, https://arxiv.org/abs/2203.10342.
  The `Xi e_lambda` basis through which `nabla_*` is expanded.
