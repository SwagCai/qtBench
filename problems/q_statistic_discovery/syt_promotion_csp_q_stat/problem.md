# Promotion Intrinsic Statistic

## Task

Find a statistic `statistic(tableau)` on standard Young tableaux that returns a
**nonnegative integer** such that, for every public shape `lambda`,

```text
C_lambda(q) = sum_{T in SYT(lambda)} q^{statistic(T)},
```

where `C_lambda(q)` is the least-degree cyclic sieving polynomial of the
Schuetzenberger action defined below on `SYT(lambda)`. This action is the inverse
of the operator that Pon and Wang call promotion (they call the convention below
dual-promotion); inverse actions have the same orbit polynomial. On rectangles
the answer is a theorem; on **staircases** it is open, and is the second bullet of
Problem 1.1 of Pon and Wang.

This `q_statistic_discovery` task has **no** public statistic. The single graded
exponent is the whole task, so `metadata.json` carries
`known_statistics: []` and there is no `known_statistic.py`. The fiber index,
the shape, is read from the object rather than submitted.

### Mathematical background

The action `d` is the bijection of `SYT(lambda)` that deletes the entry `1`, slides
the hole southeast by jeu de taquin, writes `n + 1` in the vacated outer corner and
subtracts `1` from every entry. Thus `d` is dual-promotion in Pon and Wang's
terminology, equivalently the inverse of their promotion. Let `Z/N` act on
`SYT(lambda)` through `d`, with

```text
N = rc            for a rectangle lambda = c^r        (Haiman: d^{rc} = id),
N = k(k+1)        for a staircase lambda = sc_k       (twice the number of cells).
```

The staircase modulus is the one forced by Pon and Wang's promotion-equivariant
embedding `SYT(sc_k) -> SYT(k^{k+1})`, whose ambient rectangle has `k(k+1)` cells.

A triple `(X, C, X(q))` exhibits the **cyclic sieving phenomenon** when
`X(zeta^e)` counts the points of `X` fixed by `a^e`, for `zeta` a primitive `N`-th
root of unity. Given the action, one CSP polynomial always exists: grouping `X` into
orbits and summing

```text
C_lambda(q) = sum_{orbits O} (1 + q^{N/|O|} + ... + q^{(|O|-1)N/|O|})
```

gives the least-degree representative of the coset of CSP polynomials modulo
`q^N - 1`. The task here is the stronger requirement that this polynomial also
be the generating function of an **intrinsic statistic** on `X`.

**Automatic scoring is mechanical; mathematical acceptance requires semantic review.**
Because the target is *defined* from the
orbits, the construction "walk this tableau's promotion orbit, take its
lexicographically smallest element as the origin, return the number of steps times
`N / |O|`" reproduces `C_lambda(q)` exactly, on every shape, rectangles included. It
is a deterministic function of the tableau, it is roughly forty lines, and **the
numerical checker cannot reject it**. This limitation is explicit because a promotion is
`O(rows + columns)` work, not `O(n)`, so walking a full orbit of a `990`-cell
staircase costs about `0.1` seconds -- comfortably inside the resource budget at every
probe size. Combined with the published rectangular answer below it passes every
lower-level evaluator stage, which has been verified. Enlarging the probes does not help: the
cost grows only like `n^{3/2}`.

The public CLI runs the ordinary checker and can issue an automatic pass, including
for this shortcut. A subsequent judge or reviewer must assess mathematical substance.
What is wanted is an *intrinsic* statistic -- built from
descents, diagonals or local patterns, in the way the rectangular answer below is --
and only reading the submission can establish that. Promotion is deliberately not
exposed on the objects, which makes the orbit construction visible in the source
but does not prevent it. `docs/cheating/taxonomy.md` records the mechanism and
`tests/problems/test_promotion_problem.py` pins the fact that it passes.

**The solved family.** Rhoades proved that promotion on a rectangle exhibits the CSP
with the major index. Concretely, on every public rectangle

```text
statistic(T) = (maj(T) - n(lambda)) mod N,     n(lambda) = sum_i (i - 1) lambda_i,
```

reproduces `C_lambda(q)` exactly; the generator checks this shape by shape. **An
answer must reproduce it on rectangles**, which is `19` of the `22` public cases and
a substantial public correctness constraint -- though note that it constrains the
*distribution*, not the value tableau by tableau, so it does not by itself exclude
the construction described above.

**The open family.** For staircases no such statistic is known. Pon and Wang list
three tasks of increasing difficulty: find a counting formula for `SYT(sc_k)` whose
`q`-analogue sieves, find a natural statistic on `SYT(sc_k)` whose generating
function sieves, or find one statistic on `SYT(lambda)` that sieves for every shape
and restricts to `maj` on rectangles. The public data here poses the second task,
with rectangular calibration motivated by the third.

**Anchors the answer must satisfy**, all verified by the generator over the whole
public range:

```text
C_lambda(1) = |SYT(lambda)|                       every shape
deg C_lambda < N                                  the least-degree representative
C_lambda(zeta^e) = #Fix(d^e)                      every N-th root of unity
C_lambda = distribution of (maj - n(lambda)) mod N on every rectangle
```

The root-of-unity identities are checked exactly, by dividing by cyclotomic
polynomials over the integers rather than evaluating numerically.

## Objects

The benchmark **object** is a standard Young tableau whose shape is either a
rectangle `c^r` with `c, r >= 2` or a staircase `sc_k = (k, k-1, ..., 1)` with
`k >= 2`. Single rows and single columns are excluded: their tableau set is a
singleton. The two families are disjoint, so the modulus `N` is well defined, and
the shape is read off the object.

Tableaux use English notation (`rows[0]` is the longest row) and the canonical
encoding is the rows separated by `"/"`. For example

```text
1,2,3/4,5/6
```

is the tableau of staircase shape `sc_3` whose first row is `1 2 3`. The public
fibers range from `2` tableaux up to `24024`.

The Python submission receives a `PromotionTableau` object with:

- `tableau.n`, `tableau.size` (the number of cells) and `tableau.rows`
- `tableau.shape`, `tableau.is_rectangle`, `tableau.is_staircase`
- `tableau.modulus` (`= N`), `tableau.cells`
- `tableau.descent_set()`, `tableau.maj()`, `tableau.comaj()`
- `tableau.shape_charge()` (`= n(lambda)`)

The descent statistics and `n(lambda)` are exposed because together they are the
answer on the rectangular family, not because they are graded variables of the
target. Promotion is deliberately **not** exposed, for the reason given above.

## Public Statistics

None. The single graded exponent belongs to the discovery task, so
`metadata.json` carries `known_statistics: []` and there is no
`known_statistic.py`. What is public instead is the list of identities above,
every one of which the generator verifies over the whole public range.

## Public Data

`data/polynomials.json` contains one case per public shape: the `3` staircases
`sc_2, sc_3, sc_4` and the `19` rectangles `c^r` with `c, r >= 2` and at most `16`
cells, `22` cases holding `41894` tableaux in all. Each case lists its `shape`,
`cells`, `modulus` and terms

```json
[q_exponent, coefficient]
```

so `C_lambda(q) = sum coefficient * q^{q_exponent}`, with zero coefficients omitted.
Every coefficient is positive, the coefficients of one case total `|SYT(lambda)|`,
and every exponent is below `N`.

The staircase `sc_5` is **not** in the public range: materializing its `292864`
tableaux peaks at about `168` MB, too close to the checker's `256` MB per-case budget
to be safe. A proposal should still be checked there, and
on `sc_6` if it can be afforded.

`data/q_equals_1.json` contains the `q = 1` specialization: for each case the single
term `[shape, |SYT(lambda)|]`. Unlike the other problems this marginal is **not a
hint**: `C_lambda(1) = |SYT(lambda)|` holds because the orbits partition the fiber,
whatever the submitted statistic is. It is kept as a structural check on the object
model -- that every object of a case really has that shape -- and it is checked from
the same enumeration pass.

`data/instances.json` lists the public objects for shapes with at most `12` cells.
It carries no statistic values, because there are none to publish.

The targets are computed by the maintainer generator from the promotion orbits
directly.

The shipped data is cross-checked in `tests/problems/test_promotion_problem.py`
against promotion computed a second way -- as the composition of Bender-Knuth
involutions rather than by jeu de taquin -- from which every case's orbit structure and
sieving polynomial is rebuilt, and against Rhoades' statistic on the rectangular
cases.

**`data/instances.json` is a sample, not the scored set.** It lists 2,140 objects over 15 of the 22 scored fibers, while scoring runs over all 41,894 objects of the range in `data/polynomials.json`. Its `instances_max_*` field bounds that sample only. Enumerate the full scored range with `qtbench.combinatorics` before trusting a proposal.

## Submission

Submit a short, self-contained Python file defining:

```python
def statistic(tableau) -> int:
    ...
```

The return value must be a nonnegative `int`. See `docs/checker.md` for the
admission checks; `examples/promotion_rectangle_maj_submission.py` is the answer on
the solved family (correct on all `19` rectangles, wrong on all `3` staircases).

To score it:

```bash
uv run --frozen python scripts/evaluate/evaluate_scored_submission.py promotion path/to/submission.py
```

This command returns the ordinary automatic verdict after the standard admission
checks. Passing is necessary but not sufficient for a genuine result: subsequent
semantic review must distinguish an intrinsic statistic from orbit reconstruction.
The [inference scaffold](../../../inference/README.md) provides the
checker-before-judge workflow; this checker itself does not implement semantic
review.

### Recommended advisory AI review

For this problem, using the optional AI judge as an **additional anti-cheating
review is especially strongly recommended**, more so than for the other tasks.
The orbit-walk construction described above can satisfy the complete numerical,
replay, value and resource pipeline while still merely reconstructing the target
from the defining promotion action. Detecting that distinction requires reading
the submitted algorithm and judging its mathematical meaning, which is exactly
the kind of semantic warning the AI judge can help an expert surface.

For example, after configuring the selected provider credential, an OpenAI review
can be requested with:

```bash
uv sync --extra ai-judge-openai --locked
uv run --extra ai-judge-openai --locked qtbench-ai-judge \
  22 path/to/submission.py --provider openai --model MODEL_ID
```

This review is a **second opinion for the human expert, not a proof of
intrinsicness and not an automatic verdict**. A low-risk AI assessment cannot
certify a proposal, and an elevated-risk assessment does not by itself reject
one; disguised orbit reconstruction can be missed and legitimate mathematics
can be misclassified. Acceptance still requires expert source review, informed
by the proposal's mathematical explanation and, when used, the AI judge's
advisory findings. The AI receipt must remain non-authoritative and must never be
treated as an automatic checker pass or failure. See `docs/ai_judge.md` for the
provider, privacy and receipt protocol.

## Scoring

Automatic admission uses the ordinary checker: capability screening and source
economy precede public marginal and exact coefficient checks, followed on a
numerical match by fresh-namespace shuffled replay and resource gates. The CLI
issues a normal mechanical pass or failure with a
provenance receipt. A pass is necessary but not sufficient for mathematical
acceptance; subsequent judge or reviewer assessment must detect semantic cheating.

Here, no checker stage is decisive. The target is defined from the orbits of the
promotion action, so
recomputing the definition reproduces it exactly, and doing so is cheap enough to
clear every numerical gate. Those gates still do their usual work against literal
answer tables, call-order tricks and exhaustive enumeration, but mathematical acceptance
requires subsequent semantic source review. The staircase statistic remains unknown, but this task rests on a
weaker automatic-verification footing than
problems `14`, `15`, `16` and `21`, where recomputing the target is infeasible.

## References
- Steven Pon and Qiang Wang, "Promotion and evacuation on standard Young tableaux of
  rectangle and staircase shape", Electronic Journal of Combinatorics 18 (2011),
  paper 1.18, arXiv:1003.2728, https://arxiv.org/abs/1003.2728. States Problem 1.1 -- the task posed
  here -- constructs the promotion-equivariant embedding
  `SYT(sc_k) -> SYT(k^{k+1})` that fixes the staircase modulus, and observes that in
  nearly every interesting instance of the CSP the polynomial is the generating
  function of an intrinsic statistic.
- Victor Reiner, Dennis Stanton, and Dennis White, "The cyclic sieving phenomenon",
  Journal of Combinatorial Theory Series A 108 (2004), 17-50,
  https://doi.org/10.1016/j.jcta.2004.04.009. The definition of the phenomenon.
- Brendon Rhoades, "Cyclic sieving, promotion, and representation theory", Journal of
  Combinatorial Theory Series A 117 (2010), 38-76,
  arXiv:1005.2568, https://arxiv.org/abs/1005.2568. The rectangular case: promotion on `SYT(c^r)`
  exhibits the CSP with the major index, which is the solved family here.
- Mark Haiman, "Dual equivalence with applications, including a conjecture of
  Proctor", Discrete Mathematics 99 (1992), 79-113,
  https://doi.org/10.1016/0012-365X(92)90368-P. The order of promotion on rectangular
  and staircase shapes.
- M.-P. Schützenberger, "Promotion des morphismes d'ensembles ordonnés",
  Discrete Mathematics 2(1) (1972), 73-94,
  https://doi.org/10.1016/0012-365X(72)90062-3. Introduces the promotion
  operation used here.
