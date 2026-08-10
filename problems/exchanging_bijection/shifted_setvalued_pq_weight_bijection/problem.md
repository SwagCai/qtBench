# Set-valued shifted P/Q weight-preserving bijection

## Task

Construct the explicit weight-preserving bijection in Corollary 4.1 of Chiu and
Marberg. For each strict partition `mu`, it maps

```text
SetShYT_Q(mu) disjoint-union union_{lambda in Lambda^-(mu)} SetShYT_P(lambda:mu)
```

to the analogous union over `Lambda^+(mu)`. The paper calls a bijective proof an
open problem and says that even `mu = (3,1)` has no known straightforward map.
The one-row case is known and is not scored.

`Lambda(mu)` consists of strict partitions obtained by adding at most one box
to each row of `mu`. An extension is positive or negative according as
`(-1)^(number of added columns + number of added boxes)` is `+1` or `-1`.
The map must preserve the complete content vector: primes are ignored, but every
underlying positive integer retains its multiplicity.

## Objects and encoding

Entries use ranks `1,2,3,4,...` for the ordered alphabet
`1' < 1 < 2' < 2 < ...`. Each cell is a nonempty set of ranks. As in the cited
paper, shifted diagrams use **French notation**: row `1` is the bottom row, row
`i` begins in column `i`, and larger row indices lie above smaller ones. Rows and
columns are weakly increasing by `max(left/below) <= min(current)`; an unprimed
letter cannot repeat in a column and a primed letter cannot repeat in a row.

An encoding has four semicolon-separated fields: family (`Q` or `P`), `mu`,
shape, and the cells from bottom row to top row, left to right within each row.
Parts use commas, cells use `|`, and ranks inside a cell use `.`. For example,

```text
Q;3,1;3,1;1|3|5|7
```

For `P` objects, the diagonal rule is exactly the paper's `unprime_max`
condition. In a row extended beyond `mu`, no diagonal prime is allowed. In an
unextended row, at most one diagonal prime is allowed and it must be the largest
rank in that cell. A `Q` object is always on the source side; a `P` object's
extension sign determines its side.

Submissions receive a `ShiftedSetValuedTableau` with `tableau.encoding`,
`tableau.family`, `tableau.mu`, `tableau.shape`, `tableau.cells`,
`tableau.content`, `tableau.entry_count`, `tableau.size`, `tableau.side`, and
`tableau.feature_dict()`. Define both:

```python
def forward(tableau) -> str:
    ...

def inverse(tableau) -> str:
    ...
```

## Public data and scoring

The seven scored fibers use `mu = (3,1)` and `(3,2)`. The latter includes
contents for which the negative `lambda = (4,3)` summand is nonempty. The
adjacent generator enumerates every source and target object and verifies equal
fiber sizes. `data/instances.json` is a sample, not the scored set.

The checker requires canonical outputs on the correct side, full-content
preservation, and both round trips on every source and target object. It repeats
the check in a fresh shuffled namespace, then uses larger valid tableaux for
value, time, memory, canonical-output, content, side, and round-trip gates.

Run:

```bash
uv run --frozen python scripts/evaluate/evaluate_scored_submission.py shifted-pq path/to/submission.py
```

Passing is necessary, not sufficient for a genuine uniform bijection.

## References

- Yu-Cheng Chiu and Eric Marberg, "Expanding K-theoretic Schur Q-functions",
  *Algebraic Combinatorics* 6 (2023), 1419--1445, Corollary 4.1 and the open
  problem immediately following it, https://doi.org/10.5802/alco.312 and
  https://arxiv.org/abs/2111.08993.
