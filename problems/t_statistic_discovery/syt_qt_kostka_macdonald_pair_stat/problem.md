# Modified (q,t)-Kostka Standard Tableau Statistic Pair

## Task

Find a pair of statistics `statistic(tableau) -> (stat_q, stat_t)` on pairs
`(mu, T)`, where `T` is a standard Young tableau of shape `lambda`, such that the
joint distribution over `SYT(lambda)` is the modified (q,t)-Kostka polynomial:

```text
sum_{T in SYT(lambda)} q^stat_q(mu, T) t^stat_t(mu, T) = K~_{lambda mu}(q, t)
```

for every pair of partitions `lambda, mu |- n`.

This `t_statistic_discovery` task is the only one with **no** public statistic,
so the submission supplies both exponents at once. This is data, not a task
type: `metadata.json` carries `known_statistics: []` and no
`known_statistics_file`. The problem remains in the ordinary
`t_statistic_discovery` folder, just as problem `12` does with its two public
statistics.

The **modified Macdonald polynomial** `H~_mu(X; q, t)` is defined by its Schur
expansion

```text
H~_mu(X; q, t) = sum_{lambda |- n} K~_{lambda mu}(q, t) s_lambda(X),
```

and its coefficients `K~_{lambda mu}(q, t)` are the **modified (q,t)-Kostka
polynomials**. Haiman's proof of the `n!` conjecture, via the Hilbert scheme of
points in the plane, shows that

```text
K~_{lambda mu}(q, t) in N[q, t],
```

so each `K~_{lambda mu}` counts *something*. Assaf's dual-equivalence graphs give
a general positive combinatorial formula for these Schur coefficients, but not
the direct standard-tableau statistic pair sought here. The
Haglund-Haiman-Loehr formula gives a combinatorial expansion of `H~_mu` in the
**monomial** basis; dual equivalence provides a positive route from the relevant
quasisymmetric data to its Schur coefficients.

The formulation asked for here is the one Macdonald originally proposed and the
one Zabrocki uses in the solved special cases: the objects are the standard
Young tableaux of shape `lambda` and the two statistics depend on `mu`. It is
forced by

```text
K~_{lambda mu}(1, 1) = f^lambda = |SYT(lambda)|,
```

which holds for every `mu`, since `H~_mu(X; 1, 1) = (x_1 + x_2 + ...)^n`. So each
public case has exactly as many monomials, counted with multiplicity, as the
fiber has objects: every tableau contributes exactly one `q^i t^j`.

Partial results exist and are the natural place to start, but they concern
distinct families. Fishel treats `mu` with at most two columns; Lapointe and
Morse treat two-part `mu`; Zabrocki gives standard-tableau statistics for the
two-column family and for `mu = (3, 2^a, 1^b)` or `(4, 2^a, 1^b)`. Assaf's dual
equivalence graphs give a general positive combinatorial Schur expansion, but a
uniform rule assigning a `(q,t)` statistic pair directly to every tableau in
`SYT(lambda)` for arbitrary `mu` remains open.

## Objects

A **standard Young tableau** of shape `lambda |- n` is a filling of the Young
diagram of `lambda` with `1, ..., n`, each once, increasing left to right along
rows and top to bottom down columns (English notation: `rows[0]` is the longest
row). An object of this family is a pair `(mu, T)` with `mu |- n` and `T` a
standard Young tableau with `n` cells; the shape `lambda` is read off `T`.

The canonical encoding is `mu + "|" + rows`, with `mu` comma-separated and the
rows of `T` separated by `"/"`. For example the `n = 3` object with `mu = (2, 1)`
and `T` of shape `lambda = (2, 1)` whose first row is `1 2` and whose second row
is `3` is

```text
2,1|1,2/3
```

The Python submission receives a `KostkaStandardTableau` object with:

- `tableau.n`, `tableau.size` (`= n`)
- `tableau.mu`, `tableau.shape` (`= lambda`), `tableau.rows`
- `tableau.cells` (`cells[v - 1]` is the 1-based `(row, column)` of the entry `v`)
- `tableau.descent_set()`, `tableau.maj()`, `tableau.comaj()`

The descent statistics are exposed because they are the answer at the two
extreme `mu` (see below), not because they are graded variables of the target.

## Public Statistics

None. Both exponents belong to the discovery task, so
`metadata.json` carries `known_statistics: []` and there is no
`known_statistic.py`. What the public data does pin down is the following list
of identities; every one of them is verified by the generator on the whole
public range, and together they constrain the pair tightly.

**Both extremes are classical.** With `maj(T) = sum_{i in Des(T)} i` the usual
major index,

```text
K~_{lambda (n)}(q, t)   = sum_{T in SYT(lambda)} q^maj(T),
K~_{lambda (1^n)}(q, t) = sum_{T in SYT(lambda)} t^maj(T).
```

Thus the target forces the **distribution** of `(stat_q, stat_t)` on these
fibers to equal that of `(maj, 0)`, and symmetrically at `mu = (1^n)`. A
structural solution is expected to specialize pointwise, but the executable
contract does not enforce a particular assignment among tableaux with the same
fiber distribution.

**Conjugating `mu` swaps `q` and `t`.** From `H~_{mu'}(X; q, t) = H~_mu(X; t, q)`,

```text
K~_{lambda mu}(q, t) = K~_{lambda mu'}(t, q).
```

An answer that explains this symmetry combinatorially should turn conjugation of
`mu` into an involution on `SYT(lambda)` exchanging the two statistics. (The
classical Macdonald symmetry `K_{lambda mu}(q, t) = K_{lambda' mu'}(t, q)` is a
statement about the *unmodified* Kostka-Macdonald polynomials; the identity above
is its counterpart for `K~`.)

**Setting one variable to zero gives Hall-Littlewood.** `H~_mu(X; 0, t)` is the
modified Hall-Littlewood polynomial, so

```text
K~_{lambda mu}(0, t) = sum_{S in SSYT(lambda, mu)} t^cocharge(S),
```

the cocharge form of the Kostka-Foulkes polynomial of Lascoux and
Schuetzenberger, and by the conjugation symmetry `K~_{lambda mu}(q, 0)` is the
same sum over `SSYT(lambda, mu')` in `q`. The generator checks the two marginals
of this: `K~_{lambda mu}(0, 1) = K_{lambda mu}` and `K~_{lambda mu}(1, 0) =
K_{lambda mu'}`, the ordinary Kostka numbers. In particular `K~_{lambda mu}(0, t)`
vanishes unless `lambda` dominates `mu`.

**Degrees.** `deg_q K~_{lambda mu} <= n(mu')` and `deg_t K~_{lambda mu} <=
n(mu)`, where `n(mu) = sum_i (i - 1) mu_i`.

## Public Data

`data/polynomials.json` contains the target `K~_{lambda mu}(q, t)` for every pair
of partitions `lambda, mu |- n` with `1 <= n <= 8`: 918 cases in all. Each case
carries `n`, `lam`, `mu`, and `count = f^lambda`; each term is
`[q_exponent, t_exponent, coefficient]` and `variables` is `["q", "t"]`.

`data/q_equals_1.json` contains the `q = 1` specialization, the required
one-variable distribution of the submitted `t`-statistic (a necessary, not
sufficient, condition). Each term is `[t_exponent, coefficient]`.

`data/instances.json` lists the public objects for `n <= 6`, one `entries` list
of encodings per `(lambda, mu)` case. It carries no statistic values, because
there are none to publish.

The targets are computed by the maintainer generator from the
Haglund-Haiman-Loehr monomial formula for `H~_mu`, converted to the Schur basis
against the Kostka matrix. The range is bounded only by that computation, not by
the state of the literature: unlike problem `12`, this target can be extended.

The shipped data is then cross-checked in `tests/problems/test_kostka_problem.py`
against inputs the generator never saw: the classical extreme coefficients
`<H~_mu, s_(n)> = 1` and `<H~_mu, s_(1^n)> = q^{n(mu')} t^{n(mu)}`, and an
independent Lascoux-Schuetzenberger **charge** implementation on semistandard
tableaux. The test converts it to `cocharge(S) = n(mu) - charge(S)`, which
reproduces `K~_{lambda mu}(0, t)` for every public case with `n <= 6`. This
semistandard-tableau computation shares no code and no combinatorial model with
the `inv`/`maj` fillings of `dg(mu)`, so it independently confirms the `q = 0`
slice of every target; conjugation symmetry carries it to the `t = 0` slice.

**`data/instances.json` is a sample, not the scored set.** It lists 1,085 objects over 209 of the 918 scored fibers, while scoring runs over all 21,373 objects of the range in `data/polynomials.json`. Its `instances_max_*` field bounds that sample only. Enumerate the full scored range with `qtbench.combinatorics` before trusting a proposal.

## Submission

Submit a short, self-contained Python file defining:

```python
def statistic(tableau) -> tuple[int, int]:
    ...
```

The return value must be a `tuple` of exactly two nonnegative integers, the
exponent of `q` first and the exponent of `t` second. See `docs/checker.md` for
the admission checks. The checker adapter is `kostka`; the resource probes are
tableaux of `1024` cells and the value audit runs at `64` cells, in both cases
across row, column, hook, two-row, staircase and random shapes for `lambda` and
`mu`, with both the row- and the column-superstandard tableau of each shape.

To score it:

```bash
uv run --frozen python scripts/evaluate/evaluate_scored_submission.py kostka path/to/submission.py
```

## Scoring

After the capability and source-economy screens, the evaluator enumerates each
public fiber `SYT(lambda) x {mu}` once. From the same submitted pairs, it checks
the explicit `q = 1` marginal and every `q,t` coefficient. Only a complete match
proceeds to fresh-namespace shuffled replay, the integer-value audit, and large
adversarial tableaux under CPU and memory limits. A mismatch stops the
evaluation, and passing the marginal alone is insufficient. Every stage must
pass, though a pass is necessary but not sufficient for a genuine pair of
statistics (see `docs/checker.md`).

## References
- Ian G. Macdonald, "A new class of symmetric functions", Seminaire Lotharingien
  de Combinatoire 20 (1988), Article B20a, and *Symmetric Functions and Hall
  Polynomials*, 2nd edition, Oxford University Press (1995), Chapter VI. Defines
  the Macdonald polynomials, poses the positivity conjecture, and asks for the
  statistics on standard Young tableaux.
- Adriano M. Garsia and Mark Haiman, "A graded representation model for
  Macdonald's polynomials", Proceedings of the National Academy of Sciences 90
  (1993), 3607-3610, https://doi.org/10.1073/pnas.90.8.3607. The `n!` conjecture
  and the modified polynomials `H~_mu` used here.
- Mark Haiman, "Hilbert schemes, polygraphs and the Macdonald positivity
  conjecture", Journal of the American Mathematical Society 14 (2001), 941-1006,
  arXiv:math/0010246, https://arxiv.org/abs/math/0010246. Proves `K~_{lambda mu}(q,t) in N[q,t]`
  geometrically, without producing the objects or the statistics.
- James Haglund, Mark Haiman, and Nicholas Loehr, "A combinatorial formula for
  Macdonald polynomials", Journal of the American Mathematical Society 18 (2005),
  735-761, arXiv:math/0409538, https://arxiv.org/abs/math/0409538. The `inv`/`maj` monomial expansion
  of `H~_mu`, from which the public targets are computed.
- Mike Zabrocki, "Positivity for special cases of (q,t)-Kostka coefficients and
  standard tableaux statistics", Electronic Journal of Combinatorics 6 (1999),
  #R41, arXiv:math/9901016, https://arxiv.org/abs/math/9901016. Statistics on standard Young tableaux
  for `mu_1 <= 4`, `mu_2 <= 2`: the solved instances of exactly this formulation.
- Susanna Fishel, "Statistics for special q,t-Kostka polynomials", Proceedings of
  the American Mathematical Society 123 (1995), 2961-2969,
  https://doi.org/10.1090/S0002-9939-1995-1264811-3. The first combinatorial
  interpretation, for `mu` with at most two columns.
- Luc Lapointe and Jennifer Morse, "Tableaux statistics for two part Macdonald
  polynomials", arXiv:math/9812001, https://arxiv.org/abs/math/9812001. Operators that build standard
  tableaux and assign them a `q,t` statistic for two-part `mu`.
- Sami H. Assaf, "Dual equivalence graphs and a combinatorial proof of LLT and
  Macdonald positivity", arXiv:1005.3759, https://arxiv.org/abs/1005.3759, and "Dual equivalence
  graphs revisited and the explicit Schur expansion of a family of LLT
  polynomials", Journal of Algebraic Combinatorics 39 (2014), 389-428,
  https://arxiv.org/abs/1302.0319. The dual-equivalence framework gives a general
  combinatorial Schur expansion and proves Macdonald positivity; it does not give
  the standard-tableau statistic pair sought here.
- Alain Lascoux and Marcel-Paul Schuetzenberger, "Sur une conjecture de H. O.
  Foulkes", Comptes Rendus de l'Academie des Sciences Paris 286A (1978), 323-324.
  The charge formula for the Kostka-Foulkes polynomials recovered at `q = 0`.
- Jonah Blasiak, Mark Haiman, Jennifer Morse, Anna Pun, and George H. Seelinger,
  "A raising operator formula for Macdonald polynomials", Forum of Mathematics
  Sigma 13 (2025), arXiv:2307.06517, https://arxiv.org/abs/2307.06517. A non-positive but explicit
  Schur-basis formula, the current state of the art on the algebraic side.
- Rosa Orellana, Franco Saliola, Anne Schilling, and Mike Zabrocki, "From
  quasisymmetric to Schur expansions with applications to symmetric chain
  decompositions and plethysm", Electronic Journal of Combinatorics 31 (2024),
  #P4.23, arXiv:2404.04512, https://arxiv.org/abs/2404.04512. Provides a general method to
  recover Schur expansions from fundamental-quasisymmetric data; the paper's new
  combinatorial applications concern certain plethysm coefficients, not modified
  Kostka-Macdonald coefficients.
