# Type B q,t-Catalan Area Partner

## Task

Find a statistic `statistic(path)` on type B Catalan paths such that the joint distribution

```text
sum_path q^area(path) t^statistic(path)
```

matches the target type B q,t-Catalan polynomial `Cat(B_n; q, t)` for every tested size `n`.

This `t_statistic_discovery` task publishes one statistic, `area`, and asks for
its partner (a type B "bounce").

## Objects

A **type B Catalan path** of size `n` (Stump's model) is a word of `2n` north (`N`) and east (`E`) steps starting at `(0, 0)` that stays weakly above the diagonal `y = x`; its endpoint lies on the anti-diagonal `x + y = 2n`. These paths are counted by the type B Catalan number `binomial(2n, n)`. A path is encoded as a string, for example:

```text
NNNEEN
```

The Python submission receives a `TypeBCatalanPath` object with:

- `path.n`
- `path.steps` (the `N`/`E` word)
- `path.area_word` (per-north-step area contributions)
- `path.area()`

## Public Statistic

For the north step leaving `(x, y)`, the type B (diamond) row capacity is `y` while `y < n` and `2n - y` afterwards, and the step contributes `capacity - x`:

```text
area(path) = sum over north steps of (capacity - x).
```

The same algorithm is implemented in `known_statistic.py`.

## Public Data

`data/polynomials.json` contains the target q,t-Catalan terms for `1 <= n <= 9`; each term is `[area_exponent, partner_exponent, coefficient]`. The polynomials are q,t-symmetric and total `binomial(2n, n)`. The `n = 1` value uses the cyclic `B_1 = C_2` formula, and the `n = 2, 3, 4` values are recorded from Stump's Appendix A table. The `n = 5, 6` values are committed outputs reported to come from direct diagonal-coinvariant computations, but the code and raw work records needed to repeat those computations are not included in this repository. The values for `n = 7, 8, 9` are conditional SL2-string completions, retained as benchmark targets under the assumptions below.

More precisely, the reconstruction uses the conjectural type B SL2-string model
and assumes q,t-symmetry, the type B area specialization at `t = 1`
(equivalently at `q = 1` by symmetry), the diagonal specialization
`q^(n^2) C_n^B(q,q^(-1)) = [2n choose n]_(q^2)`, nonnegativity of the SL2
strings, and the available exact bidegree coefficients. Under these
assumptions, the recorded `n = 7, 8, 9` targets are the selected completions.
The committed artifacts report that the `n = 7` target was recovered from
known string endpoints, that `n = 8` had a unique nonnegative completion in the
model, and that the `n = 9` completion was invariant under the opposing linear
objectives used to test the remaining correction variables. The reconstruction
program and its raw solver records are not included here, so those derivation
claims cannot be independently repeated from this repository. These three are
therefore conditional benchmark targets, consistent with the stated
specializations and SL2-string model. The repository does not establish that
the displayed completions are uniquely forced by those assumptions; in
particular, the `n = 9` record reports invariance only under the tested linear
objectives. They are not presented as direct algebraic computations.

The files in `source_data/` are committed target and provenance summaries, not
derivation certificates. Some partial-coefficient entries refer to `work/`
paths that are not present in this repository. `generate_data.py` re-emits the
completed polynomials from those files and checks their total, symmetry, and
area marginal; it does not recompute the diagonal-coinvariant ranks or solve the
SL2-string reconstruction. See `source_data/README.md` for the exact boundary.

`data/q_equals_1.json` contains the `q = 1` specialization, the required one-variable distribution of the unknown partner statistic (a necessary, not sufficient, condition).

`data/instances.json` contains the public type B Catalan paths (`1 <= n <= 6`) with their `area` values.

**`data/instances.json` is a sample, not the scored set.** It lists 1,274 objects over 6 of the 9 scored fibers, while scoring runs over all 66,196 objects of the range in `data/polynomials.json`. Its `instances_max_n` field bounds that sample only. Enumerate the full scored range with `qtbench.combinatorics` before trusting a proposal.

## Submission

Submit a short, self-contained Python file defining:

```python
def statistic(path) -> int:
    ...
```

The return value must be a nonnegative integer. See `docs/checker.md` for the admission checks.

To score it:

```bash
uv run --frozen python scripts/evaluate/evaluate_scored_submission.py type-b path/to/submission.py
```

## Scoring

After the capability and source-economy screens, the evaluator enumerates each
public size once. From the same submitted values, it checks the explicit
`q = 1` marginal and every q,t coefficient. Only a complete match proceeds to
fresh-namespace shuffled replay, the integer-value audit, and large adversarial
paths under CPU and memory limits. A mismatch stops the evaluation, and passing
q=1 alone is insufficient. Every stage must pass, though a pass is necessary but
not sufficient for a genuine statistic (see `docs/checker.md`).

## References
- Christian Stump, "q,t-Fuß-Catalan numbers for finite reflection groups", Journal of Algebraic Combinatorics 32 (2010), https://doi.org/10.1007/s10801-009-0205-0.
- James Haglund, "The q,t-Catalan Numbers and the Space of Diagonal Harmonics", AMS University Lecture Series 41 (2008).
