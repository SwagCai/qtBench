# Parallelogram polyomino area/bounce exchanging bijection

## Task

For every `m x n` bounding box, find a bijection `forward(P)` from parallelogram
polyominoes to parallelogram polyominoes (of the **same** bounding box) that
exchanges the `area` and `bounce` statistics:

```text
area(P)   = bounce(forward(P))
bounce(P) = area(forward(P))
```

together with its inverse `inverse(P)`. Such a bijection is a combinatorial
proof of the symmetry of the q,t-Narayana polynomials

```text
Nara_{m,n}(q,t) = Nara_{m,n}(t,q),
```

a refinement of the q,t-Catalan symmetry. The symmetry is known analytically
(Aval-D'Adderio-Dukes-Hicks-Le Borgne, via a symmetric-functions interpretation
tying `Nara_{m,n}` to the diagonal harmonics), but no simple combinatorial
bijection is known -- exactly as for the unrefined q,t-Catalan area/bounce
exchange (problem `dyck_area_bounce_exchange`).

## Objects

A parallelogram polyomino with an `m x n` bounding box is a pair of lattice
paths from the Southwest corner `(0,0)` to the Northeast corner `(m,n)`, each
using `m` East steps `E` and `n` North steps `N`, that touch only at those two
corners. The upper (Northwest) path starts with `N` and ends with `E`; the lower
(Southeast) path starts with `E` and ends with `N`; the cells enclosed between
them form the polyomino. There are `N(m + n - 1, m)` such polyominoes, the
Narayana number.

It is encoded as the string `upper + "|" + lower`, for example the single-cell
`1 x 1` polyomino:

```text
NE|EN
```

The submission receives and returns polyominoes as such strings.

## Public Statistics

Both statistics are public; reference implementations are in
`known_statistics.py`.

- `area(P)`: the number of cells enclosed between the two paths.
- `bounce(P)`: the bounce statistic, read off the polyomino's bounce path. The
  bounce path leaves `(0,0)` with a single East step, then alternately travels
  North until it meets the East end of an East step of the upper path and East
  until it meets the North end of a North step of the lower path, until it
  reaches `(m,n)`. Its k-th maximal run of North steps contributes `k` per step
  and its k-th maximal run of East steps contributes `k - 1` per step.

## Public Data

`data/polynomials.json` contains the joint distribution

```text
Nara_{m,n}(q,t) = sum_P q^area(P) t^bounce(P)
```

for every bounding box with `2 <= m + n <= 14`; each term is
`[area, bounce, coefficient]`. This is the target the bijection must reproduce
(`area(P), area(forward(P))` must realize it). `data/q_equals_1.json` is the
`q = 1` specialization (the bounce marginal), and `data/instances.json` lists
the public polyominoes with their `area` and `bounce` values for the smaller
boxes.

**`data/instances.json` is a sample, not the scored set.** It lists 625 objects over 28 of the 91 scored fibers, while scoring runs over all 1,033,411 objects of the range in `data/polynomials.json`. Its `instances_max_*` field bounds that sample only. Enumerate the full scored range with `qtbench.combinatorics` before trusting a proposal.

## Submission

Submit a short, self-contained Python file defining:

```python
def forward(polyomino) -> str:
    ...

def inverse(polyomino) -> str:
    ...
```

`forward` and `inverse` must be mutually inverse bijections on parallelogram
polyominoes of each bounding box. See `docs/checker.md` for the admission
checks.

To score it:

```bash
uv run --frozen python scripts/evaluate/evaluate_scored_submission.py polyomino-area-bounce path/to/submission.py
```

## Scoring

After the capability and source-economy screens, the evaluator enumerates every
public polyomino once. For each polyomino, it checks that `forward` and `inverse`
produce valid polyominoes in the same bounding box, are mutually inverse, and
satisfy both exchange identities. It then checks the induced `area/bounce`
distribution against `data/polynomials.json`. A mismatch stops the evaluation.
Only a complete match proceeds to fresh-namespace shuffled replay and
large adversarial polyominoes under CPU and memory
limits, where both exchange identities are checked pointwise again. Every stage
must pass. Even then, passing is necessary but not sufficient for a genuine bijection
(see `docs/checker.md`): a construction that rank-matches within equinumerous
`(area, bounce)` bags satisfies the identities but assumes the symmetry it is
supposed to prove, and the checker cannot rule that out on its own.

## References
- Mark Dukes and Yvan Le Borgne, "Parallelogram polyominoes, the sandpile model on a complete bipartite graph, and a q,t-Narayana polynomial", Journal of Combinatorial Theory Series A 120 (2013), arXiv:1208.0024, https://arxiv.org/abs/1208.0024. Introduces the q,t-Narayana polynomials `Nara_{m,n}(q,t)` via `area` and `bounce` on parallelogram polyominoes and conjectures the q,t and m,n symmetries.
- Jean-Christophe Aval, Michele D'Adderio, Mark Dukes, Angela Hicks, and Yvan Le Borgne, "Statistics on parallelogram polyominoes and a q,t-analogue of the Narayana numbers", Journal of Combinatorial Theory Series A 123 (2014), arXiv:1301.4803, https://arxiv.org/abs/1301.4803. Proves the symmetries `Nara_{m,n}(q,t) = Nara_{m,n}(t,q) = Nara_{n,m}(q,t)` analytically via a symmetric-functions interpretation; a combinatorial bijection remains open.
- Maylis Delest and Gerard Viennot, "Algebraic languages and polyominoes enumeration", Theoretical Computer Science 34 (1984), https://doi.org/10.1016/0304-3975(84)90116-6. The Narayana enumeration `N(m + n - 1, m)` of parallelogram polyominoes by bounding box.
- Adriano Garsia and Mark Haiman, "A remarkable q,t-Catalan sequence and q-Lagrange inversion", Journal of Algebraic Combinatorics 5 (1996), https://doi.org/10.1023/A:1022476211638. Introduces the q,t-Catalan numbers `C_n(q,t)`, of which the q,t-Narayana polynomials are a Narayana refinement.
- James Haglund, "The q,t-Catalan Numbers and the Space of Diagonal Harmonics", AMS University Lecture Series 41 (2008). Textbook treatment of area, bounce, dinv, and the diagonal harmonics connection.
