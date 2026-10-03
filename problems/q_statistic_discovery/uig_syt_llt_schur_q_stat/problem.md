# Unicellular LLT Schur Coefficient Statistic

## Task

Find a statistic `statistic(graph_tableau)` on Dyck graphs paired with standard
Young tableaux that returns a **nonnegative integer** `lltstat_G(T)` such that,
for every Dyck graph `G = ([n], E)` and every `lambda |- n`,

```text
c_lambda^G(q) = sum_{T in SYT(lambda)} q^lltstat_G(T),
```

where `c_lambda^G(q)` is the coefficient of `s_lambda` in the **unicellular LLT
polynomial** of `G`:

```text
LLT_G(X; q) = sum_{lambda |- n} c_lambda^G(q) s_lambda(X).
```

This `q_statistic_discovery` task has **no** public statistic. The single graded
exponent is the whole task, so `metadata.json` carries
`known_statistics: []` and there is no `known_statistic.py`. The shape `lambda`
is read from the object rather than submitted. The checker groups each graph's
fiber by shape and compares the resulting shape-graded `q`-polynomial.

### Mathematical background

For a Dyck graph (natural unit interval graph) `G` the unicellular LLT
polynomial has the colouring formula

```text
LLT_G(X; q) = sum_{kappa : [n] -> Z_{>0}} q^{asc_G(kappa)} x_kappa,
```

the sum over **all** colourings `kappa` -- unlike the chromatic quasisymmetric
function of problem `8` there is no properness condition -- with
`x_kappa = prod_v x_{kappa(v)}` and

```text
asc_G(kappa) = #{ (i, j) in E : i < j, kappa(i) < kappa(j) }.
```

`LLT_G` is a symmetric function and is **Schur positive** (Grojnowski-Haiman),
so the expansion above exists with `c_lambda^G(q) in N[q]`. At `q = 1` every
colouring contributes `1`, so

```text
LLT_G(X; 1) = (x_1 + x_2 + ...)^n = p_1^n = sum_{lambda |- n} f^lambda s_lambda,
```

and therefore

```text
c_lambda^G(1) = f^lambda = |SYT(lambda)|.
```

That is what makes this the one-variable analogue of the `(q,t)`-Kostka problem
`13`: the objects are already fixed and already the right number, the target is
a positive `q`-polynomial, and exactly one statistic is missing. What is open is
a *combinatorial* rule: Schur positivity of general LLT polynomials is a theorem,
but no general positive objectwise formula assigning an exponent to each tableau
is known. Explicit Schur expansions that provide partial guidance have been
proved for particular graph families -- complete graphs, path graphs, lollipop
and melting lollipop graphs (Huh-Nam-Yoo), and triangle-free unit interval graphs
via a generalized cocharge (Tom).

**Three target-distribution anchors**, all verified by the generator on the
whole public range:

```text
lltstat_G(T) = 0                for the edgeless graph G (b_i = i),
lltstat_{K_n}(T) = maj(T)       for the complete graph, with maj the major index,
lltstat_G(row tableau) = 0      and     lltstat_G(column tableau) = |E|,
```

the last pair being the extreme shapes `c_{(n)}^G(q) = 1` and
`c_{(1^n)}^G(q) = q^{|E|}`. More generally the target is transpose-symmetric,

```text
c_{lambda'}^G(q) = q^{|E|} c_lambda^G(1/q),
```

the coefficientwise form of `omega LLT_G(X; q) = q^{|E|} LLT_G(X; 1/q)`. An
answer that explains this combinatorially should turn shape conjugation into a
bijection `SYT(lambda) -> SYT(lambda')` sending `lltstat_G` to `|E| - lltstat_G`.
The edgeless and one-row/one-column values are pointwise forced by singleton
support. On the complete graph, however, the checker enforces only the major-index
distribution, not `maj(T)` on each individual tableau.

## Objects

A **Dyck graph** (natural unit interval graph) `G = ([n], E)` has edge set
`E subseteq { (i, j) : 1 <= i < j <= n }` closed under "nesting to the diagonal":
if `(i, j) in E` then `(k, j) in E` for `i <= k < j` and `(i, h) in E` for
`i < h <= j`. Equivalently `G` is described by its weakly increasing
right-endpoint vector `b = (b_1, ..., b_n)` with `i <= b_i <= n`, where `(i, j)`
with `i < j` is an edge exactly when `j <= b_i`. There are `C_n` (Catalan) Dyck
graphs on `[n]`, one per Dyck path of size `n`.

A **standard Young tableau** of shape `lambda |- n` is a filling of the Young
diagram of `lambda` with `1, ..., n`, each once, increasing left to right along
rows and top to bottom down columns (English notation: `rows[0]` is the longest
row).

The benchmark **object** is a pair `(G, T)` with `T` a standard Young tableau of
`n` cells; the shape `lambda` is read off `T`. It is encoded as the string
`b + "|" + rows`, the comma-separated right-endpoint vector followed by the rows
of `T` separated by `"/"`. For example the graph
`G = ([4], {(1,2),(2,3),(2,4),(3,4)})` with the tableau of shape `(3, 1)` whose
first row is `1 2 3` is

```text
2,4,4,4|1,2,3/4
```

and the single `n = 1` object is `1|1`. The fiber of one graph is the disjoint
union of all `SYT(lambda)`, so it has as many objects as `S_n` has involutions,
and the total number of size-`n` objects is `C_n` times that.

The Python submission receives a `UnitIntervalGraphTableau` object with:

- `graph_tableau.n`, `graph_tableau.size` (`= n`)
- `graph_tableau.b` (the right-endpoint vector of `G`)
- `graph_tableau.edges` (the edge set as pairs `(i, j)` with `i < j`)
- `graph_tableau.rows`, `graph_tableau.shape` (`= lambda`)
- `graph_tableau.cells` (`cells[v - 1]` is the 1-based `(row, column)` of `v`)
- `graph_tableau.descent_set()`, `graph_tableau.maj()`, `graph_tableau.comaj()`

The descent statistics are exposed because they are the answer at the complete
graph, not because they are graded variables of the target. For adjacency on
large objects prefer the `O(n)` vector `b` over materializing `edges`: vertices
`u < v` are adjacent exactly when `v <= b[u - 1]`. The `edges` set is a
convenience for small graphs (it has `|E|` elements, which is quadratic for dense
graphs).

## Public Statistics

None. The single graded exponent belongs to the discovery task, so
`metadata.json` carries `known_statistics: []` and there is no
`known_statistic.py`. What is public instead is the list of identities above,
every one of which the generator verifies over the whole public range.

## Public Data

`data/polynomials.json` contains, for every Dyck graph on `[n]` with
`1 <= n <= 7` (all `C_1 + ... + C_7 = 625` graphs), the Schur coefficients of
`LLT_G`. Each case lists its right-endpoint vector `b` and terms
`[partition, q_exponent, coefficient]`, so the shape-graded `q`-polynomial
`c_lambda^G(q)` is `sum_q coefficient * q^q_exponent` over the terms with that
partition. The coefficients are nonnegative (Schur positivity), each
`c_lambda^G` has degree at most `|E|`, the family is transpose-symmetric as
above, and the coefficients of one graph total the size of its fiber (the number
of involutions of `S_n`). The public range holds `110817` objects in all.

`data/q_equals_1.json` contains the `q = 1` specialization: for each graph the
shape distribution `{ (lambda, f^lambda) }`. Unlike the other problems this
marginal is **not a hint**: since `LLT_G(X; 1) = p_1^n` it is just the number of
standard Young tableaux of each shape, which the fiber realizes whatever the
submitted statistic is. It is kept as a structural check on the object model and
on case identity, and it is checked from the same enumeration pass.

`data/instances.json` lists the public objects (`1 <= n <= 6`) as one `entries`
list of encodings per graph. It carries no statistic values, because there are
none to publish.

The targets are computed by the maintainer generator from the colouring formula
above -- the `q^{asc}`-weighted count of colourings of each content gives the
monomial expansion of `LLT_G`, which is then converted to the Schur basis
against the Kostka matrix. The range is bounded by that computation, not by the
state of the literature.

The shipped data is cross-checked in `tests/problems/test_llt_problem.py`
against two inputs the generator never saw: the classical evaluation
`c_lambda^{K_n}(q) = sum_{T in SYT(lambda)} q^{maj(T)}` at the complete graph,
and, for `n <= 5`, the pairing `<LLT_G, h_1^n> = sum_lambda f^lambda
c_lambda^G(q)` computed directly as the `q^{asc}` distribution over the bijective
colourings. Neither shares code with the change of basis used to build the
targets.

**`data/instances.json` is a sample, not the scored set.** It lists 11,289 objects over 196 of the 625 scored fibers, while scoring runs over all 110,817 objects of the range in `data/polynomials.json`. Its `instances_max_*` field bounds that sample only. Enumerate the full scored range with `qtbench.combinatorics` before trusting a proposal.

## Submission

Submit a short, self-contained Python file defining:

```python
def statistic(graph_tableau) -> int:
    ...
```

The return value must be a nonnegative `int`. See `docs/checker.md` for the
admission checks; `examples/llt_graph_maj_submission.py` is a signature template
(the "`G`-weighted major index", which meets all three anchors but is correct
only for `338` of the `625` public graphs).

To score it:

```bash
uv run --frozen python scripts/evaluate/evaluate_scored_submission.py llt path/to/submission.py
```

## Scoring

After the capability and source-economy screens, the evaluator enumerates every public
`(G, T)` object once, groups them by the shape of `T` and by the submitted
exponent, and checks the resulting shape-graded coefficients against
`data/polynomials.json`, together with the `q = 1` shape marginal. A mismatch
stops the evaluation. Only a complete match proceeds to fresh-namespace shuffled
replay and large adversarial objects under CPU and
memory limits. Every stage must pass, though a pass is necessary but not
sufficient for a genuine statistic (see `docs/checker.md`).

For this problem, the resource gate is a useful practical lever: `LLT_G` has no
known general positive objectwise Schur expansion of the kind requested here.
No target computation documented in the repository scales to the large
adversarial graphs within the budget, while a proposed `lltstat` is expected to
be a fast function of a single object.

## References
- Alain Lascoux, Bernard Leclerc, and Jean-Yves Thibon, "Ribbon tableaux,
  Hall-Littlewood functions, quantum affine algebras, and unipotent varieties",
  Journal of Mathematical Physics 38 (1997), 1041-1068,
  https://doi.org/10.1063/1.531807. Introduces the LLT polynomials and conjectures
  their Schur positivity.
- Ian Grojnowski and Mark Haiman, "Affine Hecke algebras and positivity of LLT
  and Macdonald polynomials", preprint (2007),
  https://math.berkeley.edu/~mhaiman/ftp/llt-positivity/new-version.pdf. Proves
  Schur positivity of LLT polynomials via Kazhdan-Lusztig theory; the proof is not
  combinatorial and produces no statistic.
- Erik Carlsson and Anton Mellit, "A proof of the shuffle conjecture", Journal of
  the American Mathematical Society 31 (2018), 661-697,
  arXiv:1508.06239, https://arxiv.org/abs/1508.06239. Contains the unit-interval-graph colouring
  formula for the unicellular LLT polynomial used to compute the public targets.
- Per Alexandersson and Greta Panova, "LLT polynomials, chromatic quasisymmetric
  functions and graphs with cycles", Discrete Mathematics 341 (2018), 3453-3482,
  arXiv:1705.10353, https://arxiv.org/abs/1705.10353. The Dyck path model for unicellular LLT
  polynomials and its parallel with the chromatic quasisymmetric function of
  problem `8`.
- JiSun Huh, Sun-Young Nam, and Meesue Yoo, "Melting lollipop chromatic
  quasisymmetric functions and Schur expansion of unicellular LLT polynomials",
  Discrete Mathematics 343 (2020), 111728,
  arXiv:1812.03445, https://arxiv.org/abs/1812.03445. Explicit Schur expansions for complete
  graphs, path graphs, lollipop graphs and melting lollipop graphs: the solved
  instances of exactly this problem.
- Foster Tom, "A combinatorial Schur expansion of triangle-free horizontal-strip
  LLT polynomials", Combinatorial Theory 1 (2021),
  arXiv:2011.13671, https://arxiv.org/abs/2011.13671. An explicit Schur-positive expansion whenever
  the associated weighted graph is triangle-free, via a generalization of
  cocharge.
- Sami H. Assaf, "Dual equivalence graphs revisited and the explicit Schur
  expansion of a family of LLT polynomials", Journal of Algebraic Combinatorics
  39 (2014), 389-428, arXiv:1302.0319, https://arxiv.org/abs/1302.0319. Schur expansions for a
  further family, by dual equivalence.
