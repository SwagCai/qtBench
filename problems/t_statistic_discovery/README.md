# t-statistic discovery

Problems in this folder give a public q-statistic and ask for the missing
t-statistic. A submission defines a function on the same combinatorial objects,
and the evaluator checks whether the joint distribution

```text
sum_object q^known_statistic(object) t^statistic(object)
```

matches the target q,t-polynomial.

Current problems:

- id `1`, `nc_area_qt_narayana_second_stat`: noncrossing partitions, known `area`, target q,t-Narayana. **Solved calibration problem**: an answer ships as the adjacent `oracle.py` and doubles as the checker's known-good fixture, so a pass here demonstrates a working pipeline rather than a discovery.
- id `3`, `type_b_area_qt_catalan_second_stat`: type B Catalan paths, known `area`, target type B q,t-Catalan.
- id `6`, `lpp_area_qt_theta_second_stat`: standardly labelled parallelogram polyominoes, known `area`, target the Theta-operator Hilbert series `<Theta_{e_{m-1}} Theta_{e_{n-1}} e_1, e_{1^{m+n-1}}>` (Problem 7.13 of arXiv:2202.05706).
- id `7`, `ddyck_area_qt_unified_delta_second_stat`: standardly labelled doubly decorated Dyck paths, known `area`, target the unified-Delta Hilbert series `<Theta_{e_k} Theta_{e_l} nabla e_{n-k-l}, e_{1^n}>` (arXiv:2312.03956). The source paper calls the missing partner a `q`-statistic; because the target is `q,t`-symmetric it is equivalently the missing `t`-statistic here.
- id `9`, `ttree_inv_qt_xi_second_stat`: standard zero-rooted tiered trees `RTT_0(mu)`, known `inv`, target the Xi-operator Hilbert series `<Xi e_mu, e_{1^{|mu|}}>` (Problem 6.5 of arXiv:2202.05706).
- id `10`, `mld_area_qt_super_nabla_second_stat`: standard multi-labelled `k^n` Dyck paths, known `area`, target the super-nabla Hilbert series `<nabla_*^k e_n, e_{1^n} (x) ... (x) e_{1^n}>` with `k + 1` factors (arXiv:2303.00560).
- id `11`, `lrp_area_qt_rectangular_delta_second_stat`: standardly labelled rise-decorated rectangular paths, known `area`, target `<([m+k]_q/[gcd(m,n)]_q) Theta_{e_k} p_{m,n}, h_{1^{n+k}}>` (arXiv:2206.00131). The source paper calls the missing partner a `q`-statistic and this target is *not* `q,t`-symmetric, so the public polynomials are its transpose.
- id `12`, `tamari_park_trivariate_third_stat`: pairs (parking function, Tamari-smaller Dyck path), known `chain` **and** `dinv`, target QtBench's unrefined Hilbert-series shadow of Equation (49) in arXiv:1105.3738. It forgets the fundamental-quasisymmetric `co(f)` refinement and is therefore a weaker benchmark-derived scalar challenge. It is the only problem with two public statistics, so its target is trivariate.
- id `13`, `syt_qt_kostka_macdonald_pair_stat`: pairs `(mu, T)` of a partition and a standard Young tableau, **no** known statistic, target the modified (q,t)-Kostka polynomial `K~_{lambda mu}(q,t)` (arXiv:math/0409538, arXiv:math/0010246). It is the only problem with no public statistic: the submission returns both exponents as a pair.
- id `18`, `gpf_sel_ut_delta_xi_second_stat`: gamma-parking functions with a
  selected subset of area cells, known `#S`, target the elementary coefficients
  of `Delta_{m_gamma} Xi e_lambda` after `q = 1 + u`.
- id `19`, `rtt_inv_qt_theta_second_stat`: standard rooted tiered trees, known
  `inv`, target the Theta-operator Hilbert series
  `<Theta_{e_mu} e_1, e_{1^{|mu|+1}}>`.
- id `20`, `lgpf_sel_ut_delta_xi_schur_second_stat`: the lattice-word,
  Schur-input companion of problem `18`, with the same selected-cell statistic
  and target `Delta_{m_gamma} Xi s_lambda` after `q = 1 + u`.
- id `21`, `tgt_inv_qt_ehrhart_second_stat`: spanning trees of connected
  threshold graphs, known graph inversion number, target the `(q,t)`-Ehrhart
  function of the associated flow polytope.

In each problem, the known statistic is the exponent of `q` (`q1` and `q2` for
problem `12`), and the missing statistic is the exponent of the last variable.
Problem `13` is the exception: it has no known statistic, so the submission
supplies both exponents.

## Task

For each object family and fiber, the public data gives the target
q,t-polynomial but not the value of the missing t-statistic on each object. The
goal is an algorithmic rule, based on the object's combinatorial structure, that
assigns a nonnegative integer and extends beyond the public cases. For problem
`13`, the rule must assign a *pair* of nonnegative integers because neither
exponent is public.

Do not use the known polynomial to assign arbitrary t-values that satisfy
coefficient constraints without describing a general statistic. After
capability and source-economy screening, scoring eliminates numerically wrong
proposals, then checks numerically correct code with fresh-namespace shuffled
replay and large adversarial time/memory probes. A
proposal must pass every stage. Passing is a necessary, not a sufficient,
condition for a genuine statistic (see `docs/checker.md`).

## Files

Each problem directory contains:

- `problem.md`: the mathematical statement, object encoding, known statistic, scoring rule, and references.
- `metadata.json`: machine-readable metadata such as the numeric problem id, descriptive problem name, task type, object family, public range, scoring rule, and submission signature.
- `known_statistic.py`: executable implementation of the public q-statistic. In problem `1`, for instance, `statistic(partition)` returns `area(partition)`. Problem `12` uses `known_statistics.py` for its two public statistics; problem `13` has neither file, because no statistic is public.
- `data/instances.json`: public objects for orientation, with their encodings and any known public-statistic values but never the missing target statistic. Except in problem `1`, it is a **sample** that covers fewer fibers than the scored range, and its `instances_max_*` field describes *that file*, not the scored set. Problem `1` instead covers its complete scored range, so its `public_max_n` is the genuine scored maximum. **The scored range is the one in `data/polynomials.json` and `metadata.json`**, and it is larger for every problem except `1`. Enumerate it yourself with `qtbench.combinatorics`; a statistic validated only against `instances.json` is validated on a fraction of what is scored.
- `data/polynomials.json`: the public target q,t-polynomials.
- `data/q_equals_1.json`: the public marginal, i.e. the required distribution of the missing t-statistic on its own. It is the `q = 1` specialization, except for problems `18` and `20`, which are graded by `u = q - 1` and record `u = 1`.
- `generate_data.py` and a problem-specific oracle when needed: public target
  reproducibility code. The scored evaluator never loads either one.

## Reading `polynomials.json`

`data/polynomials.json` has:

- `variables: ["q", "t"]`, meaning every term is ordered as q first, t second.
- `cases`, one for each public fiber.
- In each case, `count` is the number of objects in the fiber and `terms` is the canonical sparse polynomial. The fiber keys depend on the object family: `n`, `k` for noncrossing partitions, `n` for type B Catalan paths, the bounding box `m`, `n` for labelled parallelogram polyominoes, the size and decoration counts `n`, `k`, `l` for doubly decorated Dyck paths, `n`, `mu` for zero-rooted and rooted tiered trees, `n`, `k` for multi-labelled Dyck paths, `m`, `n`, `k` for rectangular paths, `n` for the Tamari pairs, `n`, `lam`, `mu` for the (q,t)-Kostka tableaux, `n`, `gamma`, `lam`, `content` for the gamma-parking functions, and `n`, `up_degrees` for the threshold-graph spanning trees.

Two groups depart from `variables: ["q", "t"]`. Problem `12` has
`variables: ["q1", "q2", "q3"]` and one extra exponent per term. Problems `18`
and `20` have `variables: ["partition", "u", "t"]`: the leading entry of a term
is the e-basis partition read off the object, and the grading variable is
`u = q - 1` rather than `q`.

Each term is:

```json
[q_exponent, t_exponent, coefficient]
```

For example, `[2, 5, 3]` means the term `3 q^2 t^5`. Terms with zero coefficient are omitted, and terms are sorted by `(q_exponent, t_exponent)`.

## Reading `q_equals_1.json`

`data/q_equals_1.json` stores the same public target after setting the leading grading variable to `1` (`q = 1`, or `u = 1` for problems `18` and `20`). It checks only the distribution of the submitted t-statistic, ignoring the public q-statistic. Each term is:

```json
[t_exponent, coefficient]
```

For example, `[5, 3]` means three public objects must have submitted t-statistic value `5`. Passing this marginal is necessary but not sufficient: the full q,t-polynomial also checks how the submitted t-values pair with `area`.

## Reading `instances.json`

`data/instances.json` lists the public objects grouped by fiber. Each problem's own `problem.md` states its entry fields. For problem `1` (Type A noncrossing partitions) each entry has:

- `partition`: a sorted list of sorted blocks.
- `area`: the known public q-statistic value.

Submissions receive the same object as a `NoncrossingPartition` instance, so they can use fields such as `blocks`, `blocks_by_max`, `block_maxima`, `block_sizes_by_max`, `nonmaximal_elements`, and `area()`.

## Quick check

Full scored check (all admission stages):

```bash
uv run --frozen python scripts/evaluate/evaluate_scored_submission.py \
  noncrossing path/to/submission.py
```

Quick public q=1 marginal diagnostic:

```bash
uv run --frozen python scripts/evaluate/evaluate_submission.py \
  problems/t_statistic_discovery/nc_area_qt_narayana_second_stat \
  path/to/submission.py \
  --q-equals-1
```

The scored command prints a short report and exits successfully only when every
gate passes. The unrestricted evaluator is a maintainer diagnostic, not a scoring
path. The scored result always reports q=1 and then the full q,t comparison;
passing the marginal alone can never produce a benchmark pass.

## Data generation

Each problem is generated by its public
`problems/t_statistic_discovery/<name>/generate_data.py`, driven by the adjacent
problem-specific oracle when one is needed. A generator enumerates the public
fibers, computes the joint distribution from the public statistics and target,
and writes the polynomial terms, instances, and marginals. The scored evaluator
never loads an oracle.
