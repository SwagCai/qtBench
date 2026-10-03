# q-statistic discovery

Problems in this folder provide a public combinatorial object family and a
public target graded by a single variable `q`, then ask for a q-graded witness
that realizes it. Most submissions return an integer statistic. Problem `8`
instead returns a composition-valued elementary-basis witness paired with the
already-public exponent `ginv`.

The number of public statistics is data, not a task type. Metadata uses either a
plural `known_statistics` list or the singular fields `known_statistic` and
`known_statistic_file`. Problem `8` intentionally uses the singular form to
publish `ginv` and asks for a composition encoding of a partition-valued partner;
problems `14`, `15`, `16`, `17`, `22`, `23` and `27` use
`known_statistics: []`. In each of those latter problems, the submission supplies
the only graded exponent, while the target's other index is read from the object.

Current problems:

- id `8`, `uig_ginv_shareshian_wachs_q_stat`: Dyck graphs (natural unit interval
  graphs) `G` on `[n]` paired with their `G`-nondescent permutations
  `sigma in D_G^0`, known statistic `ginv`, target the elementary-basis expansion
  of the Shareshian-Wachs chromatic quasisymmetric function
  `chi_G[X; q] = sum_lambda c_lambda(q) e_lambda`. The submission returns a
  **composition of `n`**, and grouping the objects by its underlying partition and
  reading off `ginv` must reproduce every `c_lambda(q)`. This is the
  Shareshian-Wachs `e`-positivity conjecture in statistic-finding form; it refines
  the Stanley-Stembridge conjecture and, via Guay-Paquet's reduction to unit
  interval orders, implies it.
- id `14`, `uig_syt_llt_schur_q_stat`: the same Dyck graphs paired with standard
  Young tableaux, no known statistic, target the Schur coefficients
  `c_lambda^G(q)` of the unicellular LLT polynomial `LLT_G[X; q]`. The shape
  `lambda` is read off the tableau, not submitted. Schur positivity is a theorem
  (Grojnowski-Haiman) with no combinatorial proof.
- id `15`, `inv_orbit_harmonics_hilbert_q_stat`: involutions of `S_n`, no known
  statistic, target the Hilbert series `H_{n,a}(q)` of the orbit harmonics quotient
  `R(M_{n,a})` of the locus of involution matrices with `a` fixed points. The fiber
  index `(n, a)` is read off the object. The fixed-point-free fiber has a
  nontrivial solution (Liu-Ma-Rhoades-Zhu); the identity and
  single-transposition fibers are elementary, while the general
  positive-fixed-point fibers remain open.
- id `16`, `match_jack_connection_q_stat`: perfect matchings of
  `N_n = {1..n} u {1h..nh}` paired with a partition `lambda` of `n`, no known
  statistic, target the Jack connection coefficients `c^lambda_{pi,sigma}(beta)` of
  Goulden and Jackson, with `beta` renamed `q`. The pair of cycle types
  `(pi, sigma) = (Lambda(delta, eps), Lambda(delta, delta_lambda))` is read off the
  object. This is the Matchings-Jack conjecture, open since 1996 and proved only for
  restricted families; the statistic must vanish exactly on the bipartite
  matchings.
- id `17`, `perm_q_eulerian_gamma_q_stat`: permutations with no double descent and no
  final descent, no known statistic, target the coefficients `a_{n,k}(q)` of the
  `q`-analogue of the Eulerian `gamma`-expansion for Carlitz's `q`-Eulerian
  polynomial. The fiber index `(n, k)` is the size and one more than the descent
  count, read off the object. Han, Jouhet and Zeng prove `a_{n,k}(q) in N[q]` by a
  recurrence and ask for a combinatorial interpretation, but do not prescribe
  these objects; the fixed-object statistic task is a QtBench-proposed strengthening.
- id `22`, `syt_promotion_csp_q_stat`: standard Young tableaux of rectangular or
  staircase shape, no known statistic, target the least-degree cyclic sieving
  polynomial of Schuetzenberger promotion. The shape is read off the object. The
  rectangles are solved (Rhoades) and the staircases are Pon-Wang's Problem 1.1.
  Its `problem.md` explains that the checker cannot distinguish the intended
  answer from a known shortcut: because the target is defined from the promotion
  orbits, a submission that walks an orbit and returns a position passes every
  numerical gate without mathematical content. The ordinary automatic checker
  issues a mechanical verdict; subsequent semantic review must detect this
  shortcut before mathematical acceptance.
- id `23`, `nc_q_kreweras_q_stat`: a QtBench-proposed natural-statistic challenge,
  not a source-verified open problem. Its objects are noncrossing partitions --
  the object family of problem `1` -- and its target is the type A `q`-Kreweras
  numbers of Reiner and Sommers, graded by the block type read off the object.
- id `27`, `asm_dpp_weight_q_stat`: alternating sign matrices, no known
  statistic, target the sum-of-parts q-enumerator of descending plane
  partitions. Stanton's Open Problem 1.4 asks for exactly this statistic; the
  target is generated independently from DPPs.

## Task

For each fiber, the public data gives the target `q`-polynomial but not the
exponent of each object. The goal is an algorithmic rule that extends beyond the
public cases and reproduces the target distribution on every fiber.

Do not use the known polynomial to hand out values that satisfy the coefficient
constraints without describing a general statistic. After capability and
source-economy screening, scoring eliminates numerically wrong proposals, then
checks numerically correct code with fresh-namespace shuffled replay and large
adversarial time/memory probes. A proposal must
pass every stage. Problem `16` has an additional pointwise large-probe gate:
the submitted value must be zero exactly on bipartite matchings. Passing is a
necessary, not a sufficient, condition for a genuine statistic (see
`docs/checker.md`).

## Files

Each problem directory contains:

- `problem.md`: the mathematical statement, object encoding, known statistic (if
  any), scoring rule, and references.
- `metadata.json`: machine-readable metadata (numeric id, name, task type, object
  family, public range, scoring rule, submission signature).
- `known_statistic.py`: executable implementation of the public `q`-statistic.
  Problems with `known_statistics: []` have no such file.
- `data/instances.json`: a **sample** of the public objects, with their known
  statistic value if there is one. It never contains the target statistic, and
  it covers fewer fibers than the scored range -- its own `instances_max_*`
  field describes *that file*, not the scored set. **The scored range is the one
  in `data/polynomials.json` and `metadata.json`.** Enumerate it yourself with
  `qtbench.combinatorics`.
- `data/polynomials.json`: the public target, one case per fiber.
- `data/q_equals_1.json`: the public `q = 1` specialization.
- `generate_data.py` and a problem-specific oracle when needed: public target
  reproducibility code. The scored evaluator never loads either one.

Problem `15` additionally ships `certify_exact.py` and the
`data/exact_certificate.json` it produces, which records the exact rank over
`QQ` behind every published coefficient together with the SHA-256 digest of the
`polynomials.json` it certifies.

## Reading `polynomials.json`

Each term lists one exponent per grading variable, followed by the coefficient.
The case header names the fiber.

For problems `8`, `14` and `23`, `variables` is `["partition", "q"]`. For
problems `8` and `14`, the case is a Dyck graph given by its right-endpoint
vector `b`; for problem `23`, it is a size `n`. Terms are

```json
[partition, q_exponent, coefficient]
```

so `[[3, 1], 2, 2]` means `2 q^2` on the partition `(3, 1)`. For problem `15`,
`variables` is `["q"]`, the fiber is the pair `(n, a)`, and terms are
`[q_exponent, coefficient]`. Problems `17`, `22` and `27` use the same term shape, with
the case given by the fiber `(n, k)`, the tableau shape, and the size `n`,
respectively. For
problem `16`, `variables` is
`["pi", "sigma", "q"]`, the case is a partition `lambda`, and terms are
`[pi, sigma, q_exponent, coefficient]`. In every case zero coefficients are omitted.
Terms are sorted lexicographically by all displayed indices in their listed order
(so the `q` exponent is the sole sort key only for the unindexed term format).

`data/q_equals_1.json` stores the same target after setting `q = 1`, graded by the
index that is *not* submitted: the partition for problems `8`, `14` and `23`, the
fixed-point count for problem `15`, the pair of cycle types for problem `16`, the
descent count for problem `17`, the shape for problem `22`, and the size `n` for
problem `27`. For
problem `8` this is the elementary expansion of Stanley's ordinary chromatic
symmetric function, a genuine necessary condition on the submitted composition. For
the others the submitted exponent cannot influence it at all
(`LLT_G[X; 1] = p_1^n`, `H_{n,a}(1) = |M_{n,a}|`,
`c^lambda_{pi,sigma}(1) = |G^lambda_{pi,sigma}|`, `a_{n,k}(1) = |Gamma_{n,k}|`,
`C_lambda(1) = |SYT(lambda)|`, `Krew_lambda(1) = Krew(lambda)`, and
`DPP(n,1) = |ASM(n)|`), so it is an
object-model and case-identity check rather than a hint. Passing the marginal
alone can never produce a benchmark pass.

## Quick check

```bash
# Full scored check (all admission stages)
uv run --frozen python scripts/evaluate/evaluate_scored_submission.py \
  uig path/to/submission.py
```

The evaluator kind is `uig` for problem `8`, `llt` for problem `14`,
`involution` for problem `15`, `mjack` for problem `16`, `qgamma` for problem `17`,
`promotion` for problem `22`, `kreweras` for problem `23`, and `asm-q` for
problem `27`. All scored commands print a short report and exit successfully
only if every gate passes. Each report shows the `q = 1` marginal before the
full comparison.

## Data generation

Public data for each problem is generated by the adjacent public
`problems/q_statistic_discovery/<problem_name>/generate_data.py` and oracle, which
compute

- problem `8`: `chi_G` from proper colorings, then a change of basis to `e`;
- problem `14`: `[m_mu] LLT_G` from all colourings of each content, then a change
  of basis to `s` against the Kostka matrix;
- problem `15`: the degree filtration of the function space on the matrix locus;
  the fast generator uses two modular computations, and `certify_exact.py`
  independently certifies the complete public range over the rational field;
- problem `16`: the integral-form Jack polynomials by Gram-Schmidt in the power-sum
  basis at exact rational `alpha`, then the Cauchy sum, then interpolation in
  `beta`;
- problem `17`: the Han-Jouhet-Zeng recurrence for `a_{n,k}(q)`, cross-checked
  against the coefficients solved out of the expansion of `A_n(t,q)`;
- problem `22`: the promotion orbits themselves, with the cyclic sieving evaluations
  checked exactly by cyclotomic division;
- problem `23`: the Reiner-Sommers closed formula, in exact integer polynomial
  arithmetic with every division checked to leave no remainder.
- problem `27`: descending plane partitions enumerated by sum of parts, with
  fiber sizes independently checked by enumerating monotone triangles/ASMs.

Each generator verifies the stated identities of its target over the whole public
range before writing the polynomial terms, instances and marginal data. The
scored evaluator never loads an oracle.
