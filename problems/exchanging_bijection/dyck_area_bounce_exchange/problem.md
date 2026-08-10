# Dyck area/bounce exchanging bijection

## Task

Find a bijection `forward(pi)` from Dyck paths to Dyck paths (of the same size)
that exchanges the `area` and `bounce` statistics:

```text
area(pi)   = bounce(forward(pi))
bounce(pi) = area(forward(pi))
```

together with its inverse `inverse(pi)`. Such a bijection is a combinatorial
proof of the symmetry of the q,t-Catalan numbers `C_n(q,t) = C_n(t,q)` -- a
long-standing open problem in algebraic combinatorics. The symmetry is known
analytically (Garsia-Haglund), but no simple combinatorial bijection is known.

## Objects

A Dyck path of semilength `n` is a lattice path from `(0,0)` to `(n,n)` using
`n` north steps `N` and `n` east steps `E` that never passes below the diagonal.
It is encoded as a string, for example:

```text
NNENEE
```

The submission receives and returns Dyck paths as such strings.

## Public Statistics

Both statistics are public; reference implementations are in
`known_statistics.py`.

- `area(pi)`: the number of full lattice squares between the path and the
  diagonal.
- `bounce(pi)`: Haglund's bounce statistic, read off the bounce path.

## Public Data

`data/polynomials.json` contains the joint distribution

```text
C_n(q,t) = sum_pi q^area(pi) t^bounce(pi)
```

for `1 <= n <= 13`; each term is `[area, bounce, coefficient]`. This is the
target the bijection must reproduce (`area(pi), area(forward(pi))` must realize
it). `data/q_equals_1.json` is the `q = 1` specialization (the bounce marginal),
and `data/instances.json` lists the public Dyck paths with their `area` and
`bounce` values.

**`data/instances.json` is a sample, not the scored set.** It lists 2,055 objects over 8 of the 13 scored fibers, while scoring runs over all 1,033,411 objects of the range in `data/polynomials.json`. Its `instances_max_*` field bounds that sample only. Enumerate the full scored range with `qtbench.combinatorics` before trusting a proposal.

## Submission

Submit a short, self-contained Python file defining:

```python
def forward(path) -> str:
    ...

def inverse(path) -> str:
    ...
```

`forward` and `inverse` must be mutually inverse bijections on Dyck paths of each
size. See `docs/checker.md` for the admission checks.

To score it:

```bash
uv run --frozen python scripts/evaluate/evaluate_scored_submission.py area-bounce path/to/submission.py
```

## Scoring

After the capability and source-economy screens, the evaluator enumerates every
public Dyck path once. For each path, it checks that `forward` and `inverse`
produce valid paths of the same size, are mutually inverse, and satisfy both
exchange identities. It then checks the induced `area/bounce` distribution
against `data/polynomials.json`. A mismatch stops the evaluation. Only a complete
match proceeds to fresh-namespace shuffled replay, the integer-value audit, and
large adversarial paths under CPU and memory limits, where both exchange
identities are checked pointwise again. Every stage must pass. Even then, passing
is necessary but not sufficient for a genuine bijection (see
`docs/checker.md`): a construction that rank-matches within equinumerous
`(area, bounce)` bags satisfies the identities but assumes the symmetry it is
supposed to prove, and the checker cannot rule that out on its own.

## References
- Adriano Garsia and Mark Haiman, "A remarkable q,t-Catalan sequence and q-Lagrange inversion", Journal of Algebraic Combinatorics 5 (1996), https://doi.org/10.1023/A:1022476211638. Introduces the q,t-Catalan numbers `C_n(q,t)`.
- James Haglund, "Conjectured statistics for the q,t-Catalan numbers", Advances in Mathematics 175 (2003), https://doi.org/10.1016/S0001-8708(02)00061-0. Introduces the bounce statistic and conjectures `C_n(q,t) = sum_pi q^area(pi) t^bounce(pi)`, hence the area/bounce symmetry.
- Adriano Garsia and James Haglund, "A proof of the q,t-Catalan positivity conjecture", Discrete Mathematics 256 (2002), https://doi.org/10.1016/S0012-365X(02)00343-6. Proves the symmetry analytically; a combinatorial bijection remains open.
- James Haglund, "The q,t-Catalan Numbers and the Space of Diagonal Harmonics", AMS University Lecture Series 41 (2008). Textbook treatment of area, bounce, dinv, and the zeta map.
