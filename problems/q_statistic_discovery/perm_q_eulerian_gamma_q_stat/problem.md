# qtBench-Proposed q-Eulerian Gamma Statistic Challenge

## Task

Find a statistic `statistic(permutation)` on permutations without double or final
descents that returns a **nonnegative integer** `qgamma(sigma)` such that, for every
`n >= 1` and every `k` with `1 <= k <= floor((n + 1) / 2)`,

```text
a_{n,k}(q) = sum_{sigma in Gamma_{n,k}} q^{qgamma(sigma)},
```

where `a_{n,k}(q)` are the coefficients in the `q`-analogue of the Eulerian
`gamma`-expansion proved by Han, Jouhet and Zeng, and

```text
Gamma_{n,k} = { sigma in S_n : des(sigma) = k - 1, sigma has no double descent
                               and no final descent }
```

is the Foata-Schuetzenberger set that realizes the coefficients at `q = 1`.

This is a **qtBench-proposed strengthening** of the open interpretation question
posed by Han, Jouhet and Zeng. Their paper asks for a combinatorial interpretation
of `a_{n,k}(q)`, but does not prescribe `Gamma_{n,k}` or an objectwise statistic on
that set. qtBench fixes these objects because they give the classical interpretation
at `q = 1`; the exact task above was not stated in the cited paper.

This `q_statistic_discovery` task has **no** public statistic. The single graded
exponent is the whole task, so `metadata.json` carries
`known_statistics: []` and there is no `known_statistic.py`. The fiber index
`(n, k)` is not submitted; it is read from the object as
`(sigma.n, sigma.descents + 1)`. The checker groups the objects by fiber and
compares the resulting `q`-polynomial.

### Mathematical background

The Eulerian polynomials `A_n(t) = sum_{sigma in S_n} t^{des sigma}` expand in the
basis `t^{k-1} (1 + t)^{n+1-2k}` with nonnegative integer coefficients `a_{n,k}`,

```text
A_n(t) = sum_{k=1}^{floor((n+1)/2)} a_{n,k} t^{k-1} (1 + t)^{n+1-2k},
```

which is where symmetry and unimodality of the Eulerian numbers come from. This is
the original instance of `gamma`-positivity, and Foata and Schuetzenberger's proof
identifies `a_{n,k}` as the number of permutations of `[n]` with `k - 1` descents,
no double descent and no final descent -- the canonical representatives of the
Foata-Strehl valley-hopping orbits.

Carlitz's `q`-Eulerian polynomial is the joint enumerator of descents and the major
index, equivalently

```text
sum_{j >= 0} [j + 1]_q^n t^j = A_n(t, q) / (t; q)_{n+1},
    A_n(t, q) = sum_{sigma in S_n} t^{des sigma} q^{maj sigma},
```

with `[m]_q = 1 + q + ... + q^{m-1}` and `(x; q)_N = (1 - x)(1 - xq) ... (1 - xq^{N-1})`.
Han, Jouhet and Zeng proved the `q`-analogue of the expansion above:

```text
A_n(t, q) = sum_{k=1}^{floor((n+1)/2)} a_{n,k}(q) t^{k-1} (-t q^k; q)_{n+1-2k},
```

with `a_{n,k}(q) in N[q]` and `a_{n,k}(1) = a_{n,k}`. Their proof is a verification
of the recurrence

```text
a_{n,k}(q) = [k]_q a_{n-1,k}(q) + (1 + q^{k-1}) q^{k-1} [n + 2 - 2k]_q a_{n-1,k-1}(q),
```

so it establishes positivity without producing any statistic. The paper asks for
combinatorial interpretations of these polynomials without fixing an object family.
qtBench proposes the Foata-Schützenberger objects above as the type `A` family on
which to seek a statistic. Han, Jouhet and Zeng prove the same expansion for
Chow-Gessel's `q`-Eulerian polynomials of type `B`, whose coefficients
`b_{n,k}(q)` are equally uninterpreted; only the type `A` strengthening is posed
here.

**Anchors the answer must satisfy**, all verified by the generator over the whole
public range:

```text
a_{n,k}(1) = |Gamma_{n,k}|                      every fiber
a_{n,1}(q) = 1                        so        qgamma(identity) = 0
q^{binom(k,2)} divides a_{n,k}(q)     so        qgamma(sigma) >= binom(k,2)
deg a_{n,k} = binom(k,2) + (k-1)(n-k)
q^{-binom(k,2)} a_{n,k}(q) is palindromic of degree (k-1)(n-k)
```

The divisibility is what the paper's Corollary 2 rests on: at `n = 2m + 1`,
`k = m + 1`, the polynomial
`q^{-binom(k,2)} a_{2m+1,m+1}(q)` is Foata and Han's `q`-tangent number. Only after
specializing `q = 1` does it become the classical tangent number
`1, 2, 16, 272, ...`. The exact exponent, the degree formula and the normalized
palindromicity are recorded as properties of the shipped data, verified fiber by
fiber, not claimed as theorems. Together they
pin the support of `qgamma` on each fiber to the interval
`[binom(k,2), binom(k,2) + (k-1)(n-k)]`, symmetrically filled.

## Objects

A permutation `sigma in S_n` has a **double descent** at `i` if
`sigma(i-1) > sigma(i) > sigma(i+1)`, and a **final descent** if
`sigma(n-1) > sigma(n)`. The benchmark **object** is a permutation with neither, and
the fiber it is graded in is `(n, k) = (sigma.n, des(sigma) + 1)`, read off the
object. Equivalently the descent set of an object is a subset of `{1, ..., n - 2}`
with no two consecutive elements, which is why `k - 1` never exceeds
`floor((n - 1) / 2)`.

The canonical encoding is one-line notation: the comma-separated values
`sigma(1), ..., sigma(n)`. For example

```text
2,1,4,3,5
```

is `21435 in Gamma_{5,3}`, with descents at `1` and `3`, and the single `n = 1`
object is `1`. The fiber sizes are the classical Eulerian `gamma`-coefficients:
`|Gamma_{n,1}| = 1` always, and for instance `|Gamma_{5,2}| = 22`,
`|Gamma_{5,3}| = 16`. There are `1, 1, 3, 9, 39, 189, 1107, 7281, 54351` objects of
size `n = 1, ..., 9`.

The Python submission receives a `GammaPermutation` object with:

- `permutation.n`, `permutation.size` (`= n`)
- `permutation.values` (the tuple `(sigma(1), ..., sigma(n))`) and `permutation(i)`
- `permutation.descent_set`, `permutation.descents` (`= k - 1`, the fiber index)
- `permutation.maj()`, `permutation.comaj()`, `permutation.inv()`

The Mahonian statistics are exposed because they are the natural first guesses --
`maj` is what grades `A_n(t, q)` itself -- not because they are graded variables of
the target. All are cheap: `maj` and `comaj` are `O(n)` and the object counts
inversions in `O(n log n)`. The resource probes reach `n = 1024`, so a submission
that recounts inversions with the quadratic double loop will exhaust the probe
budget; use the object's `inv()`.

## Public Statistics

None. The single graded exponent belongs to the discovery task, so
`metadata.json` carries `known_statistics: []` and there is no
`known_statistic.py`. What is public instead is the list of identities above,
every one of which the generator verifies over the whole public range.

## Public Data

`data/polynomials.json` contains, for every fiber `Gamma_{n,k}` with `1 <= n <= 9`
(all 25 of them), the coefficient `a_{n,k}(q)`. Each case lists its `n` and `k` and
gives terms

```json
[q_exponent, coefficient]
```

so `a_{n,k}(q) = sum coefficient * q^{q_exponent}`, with zero coefficients omitted
and terms sorted by exponent. Every coefficient is positive, the coefficients of one
case total `|Gamma_{n,k}|`, and the support and symmetry are as listed among the
anchors. The public range holds `62981` objects in all.

`data/q_equals_1.json` contains the `q = 1` specialization: for each fiber the
single term `[k - 1, |Gamma_{n,k}|]`. Unlike the other problems this marginal is
**not a hint**: `a_{n,k}(1) = |Gamma_{n,k}|` is the classical Foata-Schuetzenberger
count, which the fiber realizes whatever the submitted statistic is. It is kept as a
structural check on the object model -- that every object of a case really has
`k - 1` descents and that the case has the right size -- and it is checked from the
same enumeration pass.

`data/instances.json` lists the public objects (`1 <= n <= 8`) as one `entries` list
of encodings per fiber. It carries no statistic values, because there are none to
publish.

The targets are computed by the maintainer generator from the recurrence above and,
independently, by solving the expansion against `A_n(t, q)`.

The shipped data is cross-checked in `tests/problems/test_qgamma_problem.py` against
inputs the recurrence never sees: `A_n(t, q)` recomputed as
`sum_{sigma in S_n} t^{des} q^{maj}` over the whole symmetric group, the defining
Carlitz identity `sum_j [j+1]_q^n t^j = A_n(t,q) / (t;q)_{n+1}` re-expanded as a
truncated power series, the `gamma`-coefficients re-solved out of the expansion, and
the `q = 1` values against the enumerated fibers.

**`data/instances.json` is a sample, not the scored set.** It lists 8,630 objects over 20 of the 25 scored fibers, while scoring runs over all 62,981 objects of the range in `data/polynomials.json`. Its `instances_max_*` field bounds that sample only. Enumerate the full scored range with `qtbench.combinatorics` before trusting a proposal.

## Submission

Submit a short, self-contained Python file defining:

```python
def statistic(permutation) -> int:
    ...
```

The return value must be a nonnegative `int`. See `docs/checker.md` for the
admission checks; `examples/qgamma_inv_submission.py` is a signature template (the
inversion number, which is right on the singleton fibers and on `Gamma_{3,2}` and
wrong on every other one, as is `maj`).

To score it:

```bash
uv run --frozen python scripts/evaluate/evaluate_scored_submission.py qgamma path/to/submission.py
```

## Scoring

After the capability and source-economy screens, the evaluator enumerates every public
fiber `Gamma_{n,k}` once, groups the objects by the submitted exponent, and checks
the resulting `q`-polynomial against `data/polynomials.json`, together with the
`q = 1` descent marginal. A mismatch stops the evaluation. Only a complete match
proceeds to the fresh-namespace shuffled replay and large
adversarial objects under CPU and memory limits. Every stage must pass, though a
pass is necessary but not sufficient for a genuine statistic (see `docs/checker.md`).

The resource gate is weaker here than in the neighbouring problems because
`a_{n,k}(q)` has a short recurrence. Unlike the LLT, orbit
harmonics and Matchings-Jack targets it can be recomputed cheaply at any size. What
the gate still rules out is enumerating `Gamma_{n,k}` -- which the ranking cheat
needs in order to place a single object inside its fiber, and which is exponential.
Judge a proposal on whether it expresses a combinatorial idea, not on the gate alone.

## References
- Guo-Niu Han, Frederic Jouhet, and Jiang Zeng, "Two new triangles of `q`-integers
  via `q`-Eulerian polynomials of type `A` and `B`", The Ramanujan Journal 31
  (2013), 115-127, arXiv:1203.6736, https://arxiv.org/abs/1203.6736. Proves the expansion used here,
  its type `B` analogue for Chow-Gessel's polynomials, and states the open problem
  of a combinatorial interpretation for `a_{n,k}(q)` and `b_{n,k}(q)`.
- Leonard Carlitz, "`q`-Bernoulli and Eulerian numbers", Transactions of the
  American Mathematical Society 76 (1954), 332-350. The `q`-Eulerian polynomials
  `A_n(t, q)` and the identity that defines them.
- Dominique Foata and Marcel-Paul Schuetzenberger, "Theorie geometrique des
  polynomes euleriens", Lecture Notes in Mathematics 138, Springer-Verlag, Berlin,
  1970, arXiv:math/0508232, https://arxiv.org/abs/math/0508232. The `gamma`-expansion of the Eulerian
  polynomials and the permutations without double or final descents that count its
  coefficients -- the objects of this problem at `q = 1`.
- Louis W. Shapiro, Seyoum Getu, and Wen-Jin Woan, "Runs, slides and moments", SIAM
  Journal on Algebraic and Discrete Methods 4 (1983), 459-466. The other classical
  source for that expansion and its recurrence.
- Dominique Foata and Volker Strehl, "Rearrangements of the symmetric group and
  enumerative properties of the tangent and secant numbers", Mathematische
  Zeitschrift 137 (1974), 257-264. The valley-hopping action whose orbit
  representatives are those permutations.
- Dominique Foata and Guo-Niu Han, "Doubloons and new `q`-tangent numbers", The
  Quarterly Journal of Mathematics 62 (2011), 417-432. The `q`-tangent numbers that
  appear as `q^{-binom(k,2)} a_{2m+1,m+1}(q)`, proved positive there by the
  combinatorics of doubloons -- the one sub-family of these coefficients that does
  have a combinatorial reading.
- Chak-On Chow and Ira M. Gessel, "On the descent numbers and major indices for the
  hyperoctahedral group", Advances in Applied Mathematics 38 (2007), 275-301. The
  type `B` `q`-Eulerian polynomials whose `gamma`-coefficients `b_{n,k}(q)` are the
  companion open problem.
