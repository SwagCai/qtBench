# Matchings-Jack Statistic For Jack Connection Coefficients

## Task

Find a statistic `statistic(jack_matching)` on matchings that returns a
**nonnegative integer** `mjack(delta)` such that, for every `n >= 1` and all
partitions `lambda, pi, sigma |- n`,

```text
c^lambda_{pi,sigma}(q) = sum_{delta in G^lambda_{pi,sigma}} q^{mjack(delta)},
```

where `c^lambda_{pi,sigma}` is the **Jack connection coefficient** of Goulden and
Jackson, written in the variable `q = beta = alpha - 1`, and `G^lambda_{pi,sigma}`
is the family of matchings recalled below. This is the **Matchings-Jack
conjecture**, open since 1996, in statistic-finding form. The conjecture's own
variable is `beta`; the benchmark calls it `q` because that is what the grading
variable is called everywhere else here, and nothing else changes.

This `q_statistic_discovery` task has **no** public statistic. The single graded
exponent is the whole task, so `metadata.json` carries
`known_statistics: []` and there is no `known_statistic.py`. The fiber index
`(pi, sigma)` is not submitted; it is read from the object. The checker groups
the objects of each `lambda` by that pair and compares the resulting
`(pi, sigma)`-graded `q`-polynomial.

### Mathematical background

Jack symmetric functions `J_theta^{(alpha)}` interpolate between several classical
bases: up to normalization they are Schur functions at `alpha = 1` and zonal
polynomials at `alpha = 2`. Goulden and Jackson define the connection coefficients
by the power-sum expansion of a Cauchy sum for the integral form,

```text
sum_theta (1 / <J_theta, J_theta>_alpha) J_theta(x) J_theta(y) J_theta(z) t^{|theta|}
    = sum_n t^n sum_{lambda,pi,sigma |- n}
        c^lambda_{pi,sigma} alpha^{-l(lambda)} z_lambda^{-1} p_pi(x) p_sigma(y) p_lambda(z),
```

so `lambda` plays a distinguished role: it is the index carrying the `z_lambda^{-1}`
and the power of `alpha`. At the two classical specializations the coefficients are
the structure constants of two commutative subalgebras of `C[S_n]`: the class
algebra at `beta = 0` and the double coset algebra of `(S_{2n}, H_n)` at `beta = 1`
(Hanlon-Stanley-Stembridge). Dolega and Feray proved that
`c^lambda_{pi,sigma}` is a polynomial in `beta` and bounded its degree by

```text
d(pi,sigma;lambda) = (n - l(pi)) + (n - l(sigma)) - (n - l(lambda)).
```

What is conjectural is that this polynomial is **`beta`-positive with a matching
interpretation**. Goulden and Jackson observed that the two specializations count
matchings,

```text
c^lambda_{pi,sigma}(0) = #{ delta in G^lambda_{pi,sigma} : delta is bipartite },
c^lambda_{pi,sigma}(1) = |G^lambda_{pi,sigma}|,
```

and conjectured that a single statistic interpolates between them. Their
conjecture is more precise than the identity above: the statistic should be a
**marker of non-bipartiteness**, vanishing on `delta` if and only if `delta` is
bipartite. It has been proved for `lambda = (1^n)` and `lambda = (2, 1^{n-2})`
(Goulden-Jackson), and for `pi = sigma = (n)` (Kanunnikov-Vassilieva).
Kanunnikov-Promyslov-Vassilieva prove a related **labelled-matching variant** when
one partition is `(n)`, with an additional restriction in their matching theorem:
all but one part of the other matching-type partition are at most `3`. This is
evidence for, not a proof of, the original conjecture throughout the one-part
regime. The top-degree coefficient is known in general (Burchardt, Dolega). The
general case is open, and is one of the two conjectures -- with the `b`-conjecture
for maps -- that tie Jack polynomials to the combinatorics of surfaces.

**Anchors the answer must satisfy**, all verified by the generator over the whole
public range:

```text
mjack(delta) = 0                  exactly when delta is bipartite
c^lambda_{pi,sigma}(0) = #{ bipartite delta in the fiber }
c^lambda_{pi,sigma}(1) = |G^lambda_{pi,sigma}|
deg_q c^lambda_{pi,sigma} <= d(pi,sigma;lambda)
```

The first is the conjecture's own normalization. The checker enforces it
pointwise on every public matching and on the large resource probes, in addition
to comparing the complete distribution. The two distinguished matchings `eps`
and `delta_lambda` are bipartite, so `mjack` must vanish on both.

## Objects

Let

```text
N_n = {1, ..., n} u {1h, ..., nh}
```

and let `F_n` be the set of perfect matchings of `N_n`, of which there are
`(2n-1)!!`. For two matchings the multigraph `G(delta_1, delta_2)` has every vertex
of degree `2` and its edges alternate between the matchings, so it is a disjoint
union of even cycles; `Lambda(delta_1, delta_2)` is the partition of `n` recording
**half** the length of each cycle. Two matchings are distinguished:

```text
eps         = { {1, 1h}, ..., {n, nh} }
delta_lambda = { {1, 2h}, {2, 3h}, ..., {lambda_1, 1h},
                 {lambda_1 + 1, lambda_1 + 2h}, ... }
```

the second closing up one cycle per part of `lambda`, so both are bipartite (every
pair joins the two classes of `N_n`) and `Lambda(eps, delta_lambda) = lambda`.
Goulden and Jackson's family is

```text
G^lambda_{pi,sigma} = { delta in F_n : Lambda(delta, eps) = pi,
                                      Lambda(delta, delta_lambda) = sigma }.
```

The benchmark **object** is a pair `(lambda, delta)`: the matching together with the
partition that selects its reference matching. The fiber `(pi, sigma)` is read off
the object. Elements of `N_n` are numbered `1, ..., n` for the unhatted class and
`n + 1, ..., 2n` for the hatted one, so `delta` is a fixed-point-free involution of
`[2n]`, and the encoding is `lambda + "|" + images`, the parts of `lambda` followed
by the one-line notation of that involution. For example

```text
2|3,4,1,2
```

is `lambda = (2)` paired with `eps` in `F_2`, and the single `n = 1` object is
`1|2,1`. There are `p(n) (2n-1)!!` objects of size `n`, that is
`1, 6, 45, 525, 6615, 114345, ...`.

The Python submission receives a `JackMatching` object with:

- `jack_matching.n`, `jack_matching.size` (`= n`)
- `jack_matching.lam` (the partition `lambda`)
- `jack_matching.images` (`delta` in one-line notation on `[2n]`) and
  `jack_matching.pairs` (the same as pairs `(i, j)` with `i < j`)
- `jack_matching.reference` (`delta_lambda` in one-line notation)
- `jack_matching.is_bipartite`
- `jack_matching.epsilon_type()` (`= pi`), `jack_matching.reference_type()`
  (`= sigma`)

Bipartiteness is exposed because the conjecture pins the statistic to zero exactly
there, and the two cycle types because they tell a submission which fiber it is in;
none of them is a graded variable of the target. All are `O(n)` given the object, so
a genuine statistic can use them freely.

## Public Statistics

None. The single graded exponent belongs to the discovery task, so
`metadata.json` carries `known_statistics: []` and there is no
`known_statistic.py`. What is public instead is the list of identities above,
every one of which the generator verifies over the whole public range.

## Public Data

`data/polynomials.json` contains, for every partition `lambda` of every `n` with
`1 <= n <= 6` (29 cases), the connection coefficients `c^lambda_{pi,sigma}(q)` for
all `pi, sigma`. Each case lists its `n` and `lambda` and gives terms

```json
[pi, sigma, q_exponent, coefficient]
```

so `c^lambda_{pi,sigma}(q) = sum coefficient * q^{q_exponent}` over the terms with
that pair, with zero coefficients omitted and terms sorted by
`(pi, sigma, q_exponent)`. The public range holds `1055` nonempty fibers and
`121537` objects; every coefficient is a positive integer, the coefficients of one
case total the `(2n-1)!!` matchings paired with that `lambda`, and the anchors above
hold fiber by fiber.

`data/q_equals_1.json` contains the `q = 1` specialization: for each `lambda` the
table of fiber sizes `|G^lambda_{pi,sigma}|`, as terms `[pi, sigma, coefficient]`.
Unlike the other problems this marginal is **not a hint**: it is the double coset
algebra specialization `c^lambda_{pi,sigma}(1) = |G^lambda_{pi,sigma}|`, which the
fiber realizes whatever the submitted statistic is. It is kept as a structural check
on the object model and on case identity, and it is checked from the same
enumeration pass.

`data/instances.json` lists the public objects (`1 <= n <= 5`) as one `entries` list
of encodings per `lambda`. It carries no statistic values, because there are none to
publish.

The targets are computed by the maintainer generator from the definition above: the
integral-form Jack polynomials are built at exact rational `alpha` by
Gram-Schmidt in the power-sum basis, the Cauchy sum is expanded, and the result is
interpolated in `beta` -- legitimate because the coefficients are polynomials of
degree at most `d(pi,sigma;lambda)`, which the generator re-checks on the recovered
polynomial. The range is bounded by the size of the object family, not by the state
of the literature.

The shipped data is cross-checked in `tests/problems/test_mjack_problem.py` against
inputs the generator's Jack computation never sees: the constant terms against the
bipartite matchings of each enumerated fiber *and* against the class-algebra
structure constants counted by brute force in `S_n` (the number of ways to write a
fixed permutation of type `lambda` as a product of types `pi` and `sigma`), the
values at `q = 1` against the fiber sizes, and the Jack construction itself against
its hook-product norm, its dominance triangularity, and `J_{(1^n)} = n! e_n`.

**`data/instances.json` is a sample, not the scored set.** It lists 7,192 objects over 18 of the 29 scored fibers, while scoring runs over all 121,537 objects of the range in `data/polynomials.json`. Its `instances_max_*` field bounds that sample only. Enumerate the full scored range with `qtbench.combinatorics` before trusting a proposal.

## Submission

Submit a short, self-contained Python file defining:

```python
def statistic(jack_matching) -> int:
    ...
```

The return value must be a nonnegative `int`. See `docs/checker.md` for the
admission checks; `examples/mjack_within_class_submission.py` is a signature
template (half the number of within-class pairs, which vanishes exactly on the
bipartite matchings but ignores `lambda`, and is correct on only `3` of the `29`
public cases).

To score it:

```bash
uv run --frozen python scripts/evaluate/evaluate_scored_submission.py mjack path/to/submission.py
```

## Scoring

After the capability and source-economy screens, the evaluator enumerates the objects of
every public `lambda` once, groups them by the pair of cycle types and by the
submitted exponent, and checks the resulting coefficients against
`data/polynomials.json`, together with the `q = 1` fiber-size marginal. A mismatch
stops the evaluation. Only a complete match proceeds to fresh-namespace shuffled
replay and large adversarial objects under CPU and memory
limits. On every large object, the resource-result validator also checks the
zero locus pointwise: the returned exponent must be zero if and only if the
matching is bipartite. Every stage must pass, though a pass is necessary but not
sufficient for a genuine statistic (see `docs/checker.md`).

For this problem, the resource gate has one exact pointwise anchor unavailable in
most statistic tasks: it rejects a large-probe result unless it is zero exactly
when the matching is bipartite. This blocks a constant-zero cutoff, but it does
not validate positive values on non-bipartite large probes. A public-size fitter
can therefore return zero on bipartite large probes and an arbitrary positive
integer on the others while satisfying this gate. Recomputing the full target at
size `1024` remains infeasible -- the relevant Jack transition matrices are
indexed by the partitions of `1024` -- so the gate raises the fitting cost without
eliminating the residual cutoff mechanism documented in
`docs/cheating/taxonomy.md`.

## References
- Ian P. Goulden and David M. Jackson, "Connection coefficients, matchings, maps
  and combinatorial conjectures for Jack symmetric functions", Transactions of the
  American Mathematical Society 348 (1996), 873-892,
  https://www.ams.org/journals/tran/1996-348-03/S0002-9947-96-01503-6/. Defines the coefficients
  `c^lambda_{pi,sigma}` and the matchings `G^lambda_{pi,sigma}`, states the
  Matchings-Jack conjecture, and proves it for `lambda = (1^n)` and
  `lambda = (2, 1^{n-2})`.
- Phil Hanlon, Richard P. Stanley, and John R. Stembridge, "Some combinatorial
  aspects of the spectra of normally distributed random matrices", Contemporary
  Mathematics 138 (1992), 151-174. The two specializations the conjecture
  interpolates: the class algebra at `beta = 0` and the double coset algebra of
  `(S_{2n}, H_n)` at `beta = 1`.
- Maciej Dolega and Valentin Feray, "Gaussian fluctuations of Young diagrams and
  structure constants of Jack characters", Duke Mathematical Journal 165 (2016),
  1193-1282, arXiv:1402.4615, https://arxiv.org/abs/1402.4615. Polynomiality of
  `c^lambda_{pi,sigma}` in `beta` and the degree bound `d(pi,sigma;lambda)` used
  here, without positivity.
- Andrei L. Kanunnikov and Ekaterina A. Vassilieva, "On the Matchings-Jack
  conjecture for Jack connection coefficients indexed by two single part
  partitions", Electronic Journal of Combinatorics 23 (2016), paper 1.53,
  https://www.combinatorics.org/ojs/index.php/eljc/article/view/v23i1p53. Proves the
  conjecture for `pi = sigma = (n)`.
- Andrei L. Kanunnikov, Valentin V. Promyslov, and Ekaterina A. Vassilieva, "On the
  matchings-Jack and hypermap-Jack conjectures for labelled matchings and star
  hypermaps", Electronic Journal of Combinatorics 31 (2024), paper 3.6,
  arXiv:1712.08246, https://arxiv.org/abs/1712.08246. Proves a labelled variant
  when one partition is `(n)`, under additional restrictions; in the matching
  theorem all but one part of the other matching-type partition are at most `3`.
- Adam Burchardt, "The top-degree part in the Matchings-Jack conjecture",
  Electronic Journal of Combinatorics 28 (2021), paper 2.15,
  arXiv:1803.09330, https://arxiv.org/abs/1803.09330. The leading coefficient in general, a
  necessary and sufficient condition for the degree bound to be attained, and the
  statement of the conjecture followed here.
