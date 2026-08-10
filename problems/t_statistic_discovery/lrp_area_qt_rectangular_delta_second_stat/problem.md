# Rise-Decorated Rectangular Path Delta Area Partner

## Task

Find a statistic `statistic(path)` on standardly labelled rise-decorated
rectangular paths such that the joint distribution

```text
sum_pi q^area(pi) t^statistic(pi)
```

matches the target polynomial `G_{m,n,k}(q, t)` for every tested triple
`(m, n, k)`.

This `t_statistic_discovery` task publishes one statistic, the decorated `area`,
and asks for its partner.

The target is the "Hilbert series" of the rectangular Delta symmetric function of
Iraci, Pagaria, Paolini and Vanden Wyngaerd,

```text
G_{m,n,k}(q, t) = < ([m+k]_q / [d]_q) Theta_{e_k} p_{m,n} , h_{1^{n+k}} >,
                                                            d = gcd(m, n),
```

where `Theta_f` is the Theta operator of D'Adderio, Iraci and Vanden Wyngaerd and
`p_{m,n}` is the elliptic-Hall symmetric function of Bergeron, Garsia, Sergel and
Xin; for coprime sides `p_{m,n} = e_{m,n}`, the symmetric function of the
rectangular shuffle theorem. Pairing with `h_{1^{n+k}} = e_{1^{n+k}}` restricts to
the standardly labelled objects `LRP(m+k, n+k)^{*k}`. Their open problem asks for
a statistic `qstat` realizing the full identity

```text
([m+k]_q / [d]_q) Theta_{e_k} p_{m,n}
    = sum_{pi in LRP(m+k, n+k)^{*k}} q^qstat(pi) t^area(pi) x^pi,
```

together with its rectangular-Dyck-path companion `Theta_{e_k} e_{m,n}`;
restricting to standard labellings gives exactly the scalar target above. Their
conjecture (checked by computer up to semiperimeter `13`) is the identity at
`q = 1`,

```text
( ([m+k]_q / [d]_q) Theta_{e_k} p_{m,n} ) |_{q=1}
    = sum_{pi in LRP(m+k, n+k)^{*k}} t^area(pi) x^pi,
```

so one specialization is pinned down and the second statistic remains open. The
paper notes explicitly that ignoring the decorations and taking the ordinary
rectangular `dinv` does **not** give the answer. At `k = 0`, the Dyck-path
companion is known for all `(m, n)`, while the arbitrary rectangular-path
identity is known for coprime `(m, n)` and remains conjectural in general. Every
public fiber has `k >= 1` in order to isolate the decorated problem.

### A note on nomenclature

The source paper reads `area` off the exponent of `t` and calls the missing
partner a `q`-statistic. This benchmark uses the opposite convention: the public
known statistic is the exponent of `q` and the sought partner is the exponent of
`t`. The public polynomials are therefore the **transpose** of the paper's, term
by term. Unlike the other `t`-statistic problems in this benchmark the target is
*not* `q,t`-symmetric (the factor `[m+k]_q` is a polynomial in one variable
only), so the transposition is a genuine relabelling and not a symmetry.

## Objects

A **rectangular path** of size `M x N` is a lattice path of unit North and East
steps from `(0, 0)` to `(M, N)` that **ends with an East step**. Its **rises** are
the rows whose North step immediately follows another North step, and a
**decorated** rectangular path carries a subset `dr` of them.

For a `(m+k) x (n+k)` decorated path with `k` decorated rises, the **broken
diagonal** starts at `(0, 0)` and advances horizontally by `m/n` per row, except
in decorated rows where it advances by `1`; it therefore ends at `(m+k, n+k)`.
With `col(i)` the `x`-coordinate of the `i`-th North step and `x_i` the broken
diagonal at height `i - 1`, the **area word** is `a_i = x_i - col(i)` and the
**shift** is `s = -min_i a_i >= 0`, which is `0` exactly for the paths lying
weakly above the broken diagonal (the rectangular *Dyck* paths).

A **labelling** assigns a positive integer to each North step, strictly increasing
along each maximal run of consecutive North steps; it is **standard** when the
labels are exactly `[n + k]`. `LRP(m+k, n+k)^{*k}` is the set of labelled
decorated rectangular paths of that size with `k` decorated rises.

An object is encoded as the string `path + "|" + labels + "|" + drise`, where
`path` is the North/East word, `labels` lists the label of each North step in
step order and `drise` lists the comma-separated 1-indexed decorated rise rows.
For example, one object in the smallest fiber `m = n = k = 1` is

```text
NNEE|1,2|2
```

The Python submission receives a `LabelledRectangularPath` object with:

- `path.m`, `path.n`, `path.k`, `path.width` (`= m+k`), `path.height`,
  `path.size` (`= n+k`)
- `path.path` (the North/East word), `path.labels`
- `path.rises`, `path.decorated_rises`
- `path.columns` (`col(i)`), `path.area_word` (exact `Fraction`s), `path.shift`
- `path.area()`

## Public Statistic

The decorated `area` sums the floors of the shifted area word off the decorated
rows:

```text
area(pi) = sum_{i not in dr} floor(a_i + s).
```

The same algorithm is implemented in `known_statistic.py` (in exact integer
arithmetic, by scaling the area word by `n`).

## Public Data

`data/polynomials.json` contains the target `G_{m,n,k}(q, t)` for every
`m,n,k >= 1` with semiperimeter `(m+k) + (n+k) <= 10`; this includes coprime and
non-coprime side pairs. Each term is
`[area_exponent, partner_exponent, coefficient]`. The polynomials have
nonnegative integer coefficients and total `|LRP(m+k, n+k)^{*k}|`. They are the
rectangular Delta Hilbert series above, computed in the public oracle and
independently checked to reproduce the `area` distribution at `t = 1`.

`data/q_equals_1.json` contains the `q = 1` specialization, the required
one-variable distribution of the unknown partner statistic (a necessary, not
sufficient, condition).

`data/instances.json` lists the public objects of every fiber with at most `3000`
of them, with their `area` values. It does not contain the target statistic.

**`data/instances.json` is a sample, not the scored set.** It lists 18,107 objects over 44 of the 50 scored fibers, while scoring runs over all 72,128 objects of the range in `data/polynomials.json`. Its `instances_max_*` field bounds that sample only. Enumerate the full scored range with `qtbench.combinatorics` before trusting a proposal.

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
uv run --frozen python scripts/evaluate/evaluate_scored_submission.py lrp path/to/submission.py
```

## Scoring

After the capability and source-economy screens, the evaluator enumerates each
public `LRP(m+k, n+k)^{*k}` fiber once. From the same submitted values, it checks
the explicit `q = 1` marginal and every `q,t` coefficient. Only a complete match
proceeds to fresh-namespace shuffled replay, the integer-value audit, and large
adversarial paths under CPU and memory limits. A mismatch stops the evaluation,
and passing `q = 1` alone is insufficient. Every stage must pass, though a pass
is necessary but not sufficient for a genuine statistic (see `docs/checker.md`).

## References
- Alessandro Iraci, Roberto Pagaria, Giovanni Paolini, and Anna Vanden Wyngaerd,
  "Rectangular analogues of the square paths conjecture and the univariate Delta
  conjecture", Combinatorial Theory 3 (2023), no. 2, #6,
  arXiv:2206.00131, https://arxiv.org/abs/2206.00131. Defines rise-decorated rectangular paths, the
  broken diagonal and the decorated `area`, states the `q = 1` conjecture, and
  poses the open problem of the second statistic sought in this task.
- Anton Mellit, "Toric braids and (m,n)-parking functions", Duke Mathematical
  Journal 170 (2021), 4123-4169, arXiv:1604.07456, https://arxiv.org/abs/1604.07456. Proves the
  rectangular shuffle theorem `e_{m,n} = sum_{LRD(m,n)} q^dinv t^area x^pi` for
  the Dyck-path companion; it also yields the coprime `k = 0` case discussed
  above.
- Francois Bergeron, Adriano M. Garsia, Emily Sergel Leven, and Guoce Xin, "Some
  remarkable new plethystic operators in the theory of Macdonald polynomials",
  Journal of Combinatorics 7 (2016), 671-714,
  arXiv:1405.0316, https://arxiv.org/abs/1405.0316. Defines the elliptic-Hall operators `Q_{m,n}`
  and the symmetric functions `e_{m,n}`, `p_{m,n}` used to state the target.
- Francois Bergeron, Adriano M. Garsia, Emily Sergel Leven, and Guoce Xin,
  "Compositional (km,kn)-shuffle conjectures", International Mathematics Research
  Notices 2016, 4229-4270, arXiv:1404.4616, https://arxiv.org/abs/1404.4616. The non-coprime
  extension and the `F_{a,b}` construction behind `p_{m,n}`.
- Michele D'Adderio, Alessandro Iraci, and Anna Vanden Wyngaerd, "Theta operators,
  refined Delta conjectures, and coinvariants", Advances in Mathematics 376
  (2021), 107447, arXiv:1906.02623, https://arxiv.org/abs/1906.02623. Introduces the Theta
  operators `Theta_f`.
- Angela Hicks and Emily Sergel, "A proof of the square paths conjecture",
  Journal of Combinatorial Theory Series A 156 (2018), 21-33,
  arXiv:1601.06249, https://arxiv.org/abs/1601.06249. The `dinv` correction term extended to paths
  that dip below the diagonal, on which the rectangular `dinv` is modelled.
