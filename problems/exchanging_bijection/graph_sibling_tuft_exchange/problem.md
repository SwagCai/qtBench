# Connected-graph sibling/tuft exchanging bijection

## Task

Construct mutually inverse maps on unlabeled simple connected graphs that
preserve the number of vertices and graph reduction while exchanging the
`sibling_number` and `tuft_number`:

```text
sibling_number(G) = tuft_number(forward(G))
tuft_number(G) = sibling_number(forward(G)).
```

Fürnsinn--Gangl--Rubey prove that these statistics have a symmetric joint
distribution, including separately inside every reduction fiber. Their proof is
enumerative, and Section 9 explicitly leaves an exchanging, reduction-preserving
involution open. The benchmark accepts an arbitrary bijection with an explicit
inverse; such a map still gives the requested direct combinatorial explanation.

This problem is unrelated to the path, polyomino, filling, and parking-function
exchange problems `2`, `4`, `5`, `24`, and `25`: its objects are graph
isomorphism types and its required invariant is an iterated graph reduction.

## Objects and public statistics

For a vertex `v`, write `N[v]` for its closed neighborhood. Vertices with equal
closed neighborhoods are siblings, and a leaf has degree one. Then

```text
sibling_number(G) = max_v |{u : N[u] = N[v]}| - 1,
tuft_number(G) = max_v |{leaf u : u is adjacent to v}|.
```

The reduction of a graph other than `K_2` is obtained by repeatedly removing
all leaves and contracting every maximal sibling class to one vertex, until
neither operation applies. We use `K_2` itself as its reduction.

An unlabeled graph is encoded by the lexicographically least upper-triangle
adjacency bit word among all vertex labelings. Bits are ordered

```text
(0,1), (0,2), (1,2), (0,3), (1,3), (2,3), ...
```

and written as `n:hex`, padded to the full bit width. For example, the
four-vertex star is `4:07`. The submission receives a `ConnectedGraph` with
`encoding`, `n`, `size`, `adjacency`, `degrees`, `sibling_number()`,
`tuft_number()`, `reduction`, and `feature_dict()`, and returns a canonical
encoding string.

## Public data

`data/polynomials.json` gives

```text
sum_G q^sibling_number(G) t^tuft_number(G)
```

for every unlabeled connected graph on `1 <= n <= 7` vertices. The 996 objects
are the complete graph-atlas fibers of sizes `1, 1, 2, 6, 21, 112, 853`.
`data/instances.json` lists every object with both statistics and its reduction.
The adjacent generator obtains the graph atlas independently, canonicalizes
every entry, rejects duplicates, and verifies both ordinary and reduction-fiber
symmetry.

## Submission and scoring

Submit a short, self-contained Python file defining:

```python
def forward(graph) -> str:
    ...

def inverse(graph) -> str:
    ...
```

To score it:

```bash
uv run --frozen python scripts/evaluate/evaluate_scored_submission.py graph-sibling-tuft path/to/submission.py
```

After capability and source-economy screening, the evaluator checks every
public graph for canonical same-size images, both round trips, both exchange
identities, reduction preservation, and the full public distribution. A complete
match is replayed from a fresh namespace in shuffled order, then audited on
star/complete pairs at several much larger sizes under the requested CPU and
memory limits, together with a few seven-vertex graphs that the public range
already enumerates. The star/complete pairs are the only probes above the
public range, because checking an arbitrary large graph would need general
canonical labeling. The two extreme
graphs are each other's uniquely possible exchange image, so their canonical
outputs can be checked directly without running factorial-time graph
canonicalization at the large sizes.

Passing is necessary, not sufficient for a genuine result. Rank matching inside
the public statistic fibers would pass the finite checks while assuming the
symmetry it is meant to explain; the large probes are designed to make that
approach uneconomic. See `docs/checker.md`.

## References

- Florian Fürnsinn, Moritz Gangl, and Martin Rubey, "Unexpectedly, a symmetry on
  unlabeled graphs", arXiv:2505.03665 (2025),
  https://arxiv.org/abs/2505.03665. Theorem 1 proves joint symmetry, Theorem 2
  proves its reduction-fiber refinement, and Section 9 asks for the involution.
