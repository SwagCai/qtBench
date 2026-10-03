# Cheating-attempt taxonomy

This is a threat model for the full 30-problem benchmark, not a list of claims
that every attack has been implemented. It separates three kinds of statement:

- **confirmed**: a regression test or maintained reproducer establishes the
  behavior;
- **proved by inspection**: the claim follows directly from the scored adapter,
  problem statement, or probe generator;
- **residual risk**: the construction is possible under the checker model, but
  no passing implementation is claimed.

The distinction matters. For example, `ACTION-1` is a confirmed
all-gates bypass on problem `22`, including automatic CLI admission; subsequent
semantic review must detect it. By contrast, saying that a closed target makes ranking
more plausible does not prove that a short, scalable ranker exists for that
object family.

## Reading the catalog

Status labels describe the current scored checker:

- **blocked**: the ordinary form is rejected;
- **mitigated**: an important form is rejected, with documented bypasses;
- **open**: a practical form can still pass;
- **retired**: a historical gate or its implementation risk is no longer active;
- **outside scored path/open by design**: the mechanism belongs to an explicitly
  unrestricted diagnostic or generation path and must not be used on untrusted
  input;
- **irreducible**: no general mechanical test can separate the attack from an
  allowed program under the current unrestricted-Python model.

Severity measures the consequence *if the mechanism succeeds*, independently
of how well it is currently blocked:

- **critical**: a passing score can be produced with no evidence for the
  requested mathematical idea, or attacker-controlled code can run with the
  caller's privileges;
- **high**: the claimed objectwise or beyond-range interpretation is defeated;
- **medium**: a defense is weakened or a second attack becomes substantially
  cheaper;
- **low**: the attempt gives only a partial or fragile advantage.

Problem IDs below refer to the stable numeric IDs in the root catalogue.
“Statistic tasks” means IDs `1`, `3`, `6`--`23`, and `27`; “bijection tasks”
means IDs `2`, `4`, `5`, `24`--`26`, and `28`--`30`.

When an attack is confirmed, add a small regression test whenever the expected
behavior is mechanical and stable. Do not turn an irreducible distinction into
an opaque heuristic that can reject genuine statistics.

The **backing test** column names a test in `tests/` that verifies the row.
For a blocked or mitigated row it is a test that the attack is rejected. For
`ACTION-1` it includes both the lower-level passing reproducer and the CLI test
that blocks automatic admission. Rows marked "none possible"
have no mechanical expectation to pin -- that is what their status means.
“None currently” means that a focused mechanical gate and regression would be
possible, but neither exists in the scored path today.
`tests/problems/test_registry.py` asserts every name here resolves to a real
test.

## Catalog

| ID | Family | Typical mechanism | Status | Severity | Affected IDs | Principal check | Backing test |
|---|---|---|---|---|---|---|---|
| CAP-1 | External capability | Import, file, network, process, or reflection access | Mitigated | Critical | all | Capability screen and process audit hook | `test_capability_safety_blocks_escapes_and_dynamic_signatures`, `test_no_admitted_attribute_reaches_a_frame_or_code_object` |
| EMB-1 | Embedded answer | Literal or generated lookup table | Mitigated | High | all | Source-economy limits | `test_source_economy_rejects_oversized_sources` |
| STATE-1 | Stateful assignment | Global counter, mutable cache, or call-order schedule | Mitigated | Critical | all | Fresh single-cycle replay and repeated calls | `test_noncrossing_rejects_first_call_only_statistic`, `test_bijection_rejects_a_first_call_only_forward` |
| MARG-1 | Marginal-only fitting | Match `q=1`/`u=1` while ignoring the full joint target | Blocked | Low | statistic tasks | Exact full polynomial after the marginal | `test_q_equals_1_is_only_a_weaker_diagnostic` |
| ANCHOR-1 | Pointwise-anchor permutation | Preserve a distribution while assigning known anchor values to the wrong objects | Open | High | `13`--`15`; mitigated for `16` | No generic check; problem `16` has an exact zero-locus gate | `test_distribution_preserving_zero_locus_swap_is_rejected`, `test_large_probe_zero_locus_is_checked_pointwise` |
| CUTOFF-1 | Public-range fitting | Correct code only on scored sizes; trivial output above them | Open | High | especially statistic tasks | Additional exact cases only move the cutoff | none possible |
| ENUM-1 | Exhaustive search | Enumerate the complete object fiber per input | Mitigated | High | all | Large resource probes | `test_resource_gate_stops_time_and_memory_attacks` |
| RANK-1 | Uniform rank assignment | Rank an object in its fiber and distribute target exponents by rank | Irreducible | Critical | statistic tasks | No generic behavioral check | none possible |
| ACTION-1 | Recomputing the defining action | Recompute the group action a target is defined from and read a position off the orbit | Open | Critical | `22` confirmed | Subsequent judge/source review; mechanical checks do not distinguish the shortcut | `test_cli_scores_promotion`, `test_cli_orbit_position_receives_automatic_pass`, `test_orbit_position_construction_passes_full_admission` |
| TARGET-1 | Target-directory substitution | Point the scored CLI at attacker-selected compatible target data | Blocked | Critical | all | Scored dispatch uses only the registry-fixed problem directory | `test_scored_cli_rejects_problem_directory_override` |
| CONFIG-1 | Scoring-configuration override | Reduce probe size or choose favorable time, memory, or seed settings while retaining a scored verdict | Blocked | High | all | Fixed, reported official configuration and checker-selected secrets | `test_scored_cli_rejects_security_configuration_overrides`, `test_scored_main_records_provenance_and_replaces_inherited_seed_overrides` |
| INPUT-1 | Blocking submission input | Supply a FIFO whose writer keeps the scored reader waiting for EOF | Blocked | Medium | all | Nonblocking open, same-descriptor regular-file check, and bounded read | `test_scored_cli_rejects_fifo_without_waiting_for_eof` |
| INIT-1 | Unguarded module initialization | Retain allocations in top-level globals before resource measurement starts | Mitigated | High | all | Resource and identity probes trace allocation before submitted module execution; process RSS limits remain for numerical workers | `test_resource_gate_counts_top_level_retained_allocations` |
| IPC-1 | Parent-side result expansion | Return a compact iterable such as a huge `range` that expands when a validator consumes it in the scorer parent outside the worker resource limits | Blocked | High | `8` confirmed; other statistic tasks reviewed | Validators do not invoke iteration on non-exact containers; exact composition containers are length-bounded before copying | `test_parent_validators_do_not_render_untrusted_results`, `test_compositions_accept_only_bounded_builtin_sequences` |
| MEM-1 | Aggregate process-envelope exhaustion | Keep a worker under its individual cap while evaluator-parent and IPC allocations push their combined RSS beyond the intended envelope | Blocked | Medium | automatically scored tasks | Statistic config v3 and bijection config v4 reserve 192 MiB for the worker and 64 MiB for the parent inside a sampled 256 MiB aggregate budget | `test_aggregate_budget_rejects_incompatible_caps_before_worker_start`, `test_aggregate_preflight_reserves_ipc_before_worker_start`, `test_aggregate_wait_requires_ipc_headroom_before_receiving_payload`, `test_aggregate_wait_rejects_the_combined_parent_and_worker_rss`, `test_aggregate_wait_fails_closed_if_parent_rss_cannot_be_measured`, `test_isolated_worker_rejects_parent_growth_after_deserialization` |
| SERIAL-1 | Parent integer serialization failure | Return a valid nonnegative resource-probe integer whose decimal form exceeds the runtime limit and aborts official JSON rendering | Blocked | Medium | statistic tasks | Integer and pair validators reject values unavailable to the official JSON encoder | `test_resource_validators_reject_integers_unavailable_to_json`, `test_official_formats_report_json_unavailable_probe_integers` |
| PROV-1 | Forged scoring receipt | Run a modified launcher/interpreter or edit self-reported JSON to claim an official pass | Open | Critical | all | Trusted external invocation; informational commit, target, and submission hashes | `test_scored_main_records_provenance_and_replaces_inherited_seed_overrides` |
| DIAG-1 | Unrestricted diagnostic execution | Pass attacker-controlled Python to a diagnostic/generator CLI or loader API | Outside scored path/open by design | Critical | diagnostic/generator CLI/API | Trusted local files only; official scoring never invokes the unrestricted loader | `test_diagnostic_cli_executes_submission_with_caller_privileges`, `test_diagnostic_cli_help_warns_about_unrestricted_execution`, `test_problem_one_generator_help_warns_about_unrestricted_oracle`, `test_scored_cli_does_not_execute_rejected_top_level_side_effect` |
| INT-1 | Visible big-integer counting | Retain a large built-in `int` in a frame | Open | Medium | all | No magnitude-specific gate; source, time, and memory limits only | none possible |
| INT-2 | Ephemeral big integer | Reduce or delete a large value before resource sampling | Open | Medium | all | Time and memory limits only | none possible |
| INT-3 | Encoded big integer | Store limbs, digits, or a symbolic representation in small values | Open | Medium | all | Resource and source limits only | none possible |
| INT-4 | Cross-root scan starvation | Exhaust the former bounded value scan in an early collection | Retired | Medium | historical | Integer-magnitude inspection removed in checker version 18 | none (retired) |
| INT-5 | Profile-callback exception interception | Catch a former profiler-raised value violation | Retired | High | historical | Integer-magnitude inspection removed in checker version 18 | none (retired) |
| PROBE-1 | Probe recognition | Hardcode public objects or known deterministic probes | Mitigated | High | all; acute for `26` | Post-submission random probes | `test_hardened_probes_cover_three_scales`, `test_structural_size_covers_every_registered_probe_kind`, `test_asm_hardened_probes_use_three_effective_capped_scales`, `test_shifted_pq_hardening_uses_three_orders_without_repeating_maximum` |
| TYPE-1 | Degenerate large output | Return `None`, strings, floats, booleans, undeclared iterable types, or malformed compositions only at scale | Blocked | Low | statistic tasks | Large-probe output validation, including exact tuple/list enforcement for problem `8` | `test_noncrossing_rejects_invalid_outputs_on_large_resource_probes`, `test_compositions_accept_only_bounded_builtin_sequences` |
| BIJ-1 | Finite bijection fitting | Correct table or enumeration on public bijection sizes | Mitigated | High | bijection tasks | Large pointwise identity gates | `test_identity_gate_rejects_enumeration_bijection_at_scale` |
| BIJ-2 | Rank-matched bijection | Rank-match equinumerous statistic fibers uniformly | Irreducible | Critical | bijection tasks | No generic behavioral check | none possible |
| EXPLOIT-1 | Checker escape | Exploit the Python runtime or a checker implementation bug | Open | Critical | all | Capability screen, isolation, and red-team tests | `test_submission_audit_policy_allows_only_declared_reads` |

## Scored-checker baseline

For automatically scorable problems, the default CLI makes the following
concrete claims, all proved by source inspection and covered at the mechanism
level by the tests named above. Problem `22` uses this same pipeline:

1. The admitted source has no imports, I/O, network, process creation,
   reflection, dunder access, dynamic calls, classes, assignment expressions,
   `match` statements, or attribute writes, and binds no whitelisted builtin's
   name. `_UNSAFE_NODES` in `qtbench.evaluation.admission` is the authority for
   the rejected constructs.
2. Source is capped at 8,192 bytes, 160 lines, 1,500 tokens, 2,000 AST nodes,
   and 256 literal bytes.
3. The problem kind selects a registry-fixed target directory; no scored CLI
   argument can substitute other target data. Every public object in every
   committed target case is evaluated; the marginal and complete polynomial
   (or complete bijection identities) are compared exactly.
4. The code is loaded again in a fresh namespace, traversed in a secret
   single-cycle order, and every callable is repeated. The keyed object/output
   fingerprint must agree.
5. Fixed resource probes request size 1,024, generally at three scales, with two
   seconds, 32 MB of traced Python allocation and 8 MB of worker IPC. Official
   isolated execution reserves 192 MiB of process RSS for the worker and 64 MiB
   for the evaluator parent inside a sampled 256 MiB aggregate envelope. Tracing
   begins before submission module initialization. The exact structural size
   differs where an object's natural size is a semiperimeter, weight, or number
   of entries. Problem `27` caps its dense representation at order 256 and uses
   effective orders 64, 128, and 256 within the same memory envelope. Problem
   `28` uses orders 256, 512, and 1,024, without generating its maximum shifted
   P/Q level twice.
6. Large statistic probes have no unknown ground truth and therefore check
   resources plus output type, except that problem `16` also enforces its exact
   bipartite zero locus pointwise. Large bijection probes additionally recompute
   their pointwise side, shape, inverse, statistic, content, weight, reduction,
   or grading identities.

The official CLI records this configuration and its checker-selected run seed
in every result and exposes no security-relevant overrides. It also records
self-reported commit, target-bundle, and submission provenance. Those fields
are audit receipts, not signatures: official scoring assumes a trusted launcher,
interpreter, checker checkout, and stable target tree. These are finite sampled
properties, not an asymptotic proof, operating-system sandbox guarantee, or
remote attestation.

## Problem-aware risk map

This table records the strongest repository-supported concern for every problem.
“No specific bypass” means that only the generic finite-range, ranking, and
runtime risks above are known; it is not a proof of semantic authenticity.

| ID | Reviewer-facing assessment | Checker defenses and remaining limitation |
|---:|---|---|
| 1 | **Critical interpretation risk, proved by inspection:** this is a solved calibration problem and its answer is public in `oracle.py`. A pass demonstrates the pipeline, not discovery. | Full numerical, replay, and resource gates still test the implementation. Discovery reports must exclude it or report it separately. |
| 2 | **Critical residual (`BIJ-2`):** a uniform rank match between the `(area,bounce)` fibers would satisfy the requested exchange while assuming q,t-Catalan symmetry. | Every public path and large adversarial paths receive validity, two-sided round-trip, and both pointwise exchange checks. These reject tables and exhaustive enumerators, not a scalable rank formula. |
| 3 | **High interpretation and provenance risk, proved by inspection:** targets for `n=7,8,9` are conditional SL2-string completions, and the repository does not include the direct-rank or reconstruction derivation pipeline for `n=5,...,9`. A pass matches the committed targets, not an unconditional independent computation of type B q,t-Catalan. | Exact checks cover all committed coefficients; public aggregate records state the assumptions but do not reproduce their derivation. Generic `RANK-1` and `CUTOFF-1` remain. |
| 4 | **Critical residual (`BIJ-2`):** rank matching inside polyomino `(area,bounce)` bags can explain neither the map nor the symmetry. | Complete public boxes and large full/random polyominoes are checked pointwise for validity, round trips, and both exchanges. |
| 5 | **Critical residual (`BIJ-2`):** the analogous construction rank-matches equal `(area,bounce)` bags across transposed boxes. | The large identity gate checks box transposition, both preserved statistics, and both round trips. A uniform matcher is still observationally valid. |
| 6 | **High generic risk only:** no problem-specific passing shortcut is documented for the Theta-operator target. Symmetry makes the one-variable marginal equal the public `area` distribution, so that marginal alone is weak evidence. | The full joint target is exact; probes span several boxes and full/random shapes with canonical standard labellings. Target recomputation at scale is not claimed to be feasible. |
| 7 | **High generic risk only:** q,t-symmetry makes the marginal predictable from decorated `area`, but does not determine the joint assignment. | The full polynomial is checked over all public decoration fibers. Large probes vary shapes and use no, all-rise, all-valley, and mixed decorations. |
| 8 | **High residual (`RANK-1`), but a comparatively strong resource lever:** the output is a composition whose underlying partition must match the `ginv`-graded elementary coefficients. No closed form for those coefficients is documented. | The `q=1` partition marginal is a genuine constraint, the full partition/`ginv` target is exact, and large probes cover empty, complete, banded, and random Dyck graphs with several permutations. A semantic rank assignment remains irreducible if made scalable. |
| 9 | **High generic risk only:** no specific shortcut is documented for the Xi-operator partner on zero-rooted tiered trees. | Full joint checks plus one-tier, two-tier, fully tiered, and random large trees block sample fitting and straightforward enumeration. `CUTOFF-1` remains. |
| 10 | **High generic risk only:** no scalable recomputation or rank construction is established for the super-nabla target. | Full `(area,t)` checks are followed by large probes at `k=1,2,3` on maximal-area, zero-area, and random shapes. |
| 11 | **High generic risk only:** the target is not q,t-symmetric, so blindly swapping or copying the public area marginal is not a viable explanation. | Exact transposed target coefficients and large probes across boxes, shapes, and decoration counts are checked. Finite-range fitting remains possible. |
| 12 | **High scope risk, now explicit:** the executable target forgets the fundamental-quasisymmetric `Q_{co(f)}` refinement, so it cannot certify the cited Frobenius identity. | The item is labelled a weaker qtBench-derived Hilbert-series-shadow challenge. Large probes still defend that scalar contract, but a pass must not be reported as solving Equation (49). |
| 13 | **High semantic risk (`ANCHOR-1`) with a strong resource lever:** the classical `mu=(n)` and `mu=(1^n)` formulas are stated objectwise, but the checker observes their distributions. Values can be permuted among tableaux without changing a polynomial. | Pair outputs are type-checked; 918 public `(lambda,mu)` cases and large varied shapes are used. Recomputing general modified Kostka-Macdonald targets at size 1024 is documented as infeasible, but `CUTOFF-1` and within-fiber semantic permutations remain. |
| 14 | **High semantic risk (`ANCHOR-1`) with a strong resource lever:** a passing distribution need not equal `maj(T)` tableau by tableau on the complete-graph anchor. The shape marginal at `q=1` is structural only. | Full Schur-coefficient polynomials are exact, and large probes vary graph and tableau shapes. No scalable LLT-to-Schur recomputation is known. Edgeless and one-row/one-column anchors are forced by singleton support, but the complete-graph pointwise formula is not. |
| 15 | **High semantic risk (`ANCHOR-1`) with a strong resource lever:** the fixed-point-free formula `(n-lds(pi))/2` is a stated objectwise anchor, while scoring only its distribution; a permutation within `M_{n,0}` is invisible. | Exact certified public targets and large probes spread over fixed-point counts and matching shapes. General target recomputation requires orbit-harmonics elimination and is documented as infeasible at probe scale. The `q=1` marginal is only a fiber-size check. |
| 16 | **Mitigated semantic risk (`ANCHOR-1`):** swapping a zero and a positive exponent within one `(pi,sigma)` fiber preserves the polynomial but violates the Matchings-Jack marker property. | The public enumerator and large resource probes now enforce `mjack(delta)=0` exactly on bipartite matchings. General semantic rank assignment and target-recomputation risks remain. |
| 17 | **High residual (`RANK-1`) and source-status caveat:** the target recurrence is short and can be recomputed at arbitrary sizes, weakening the target-economy half of the defense. Han--Jouhet--Zeng ask for an interpretation but do not prescribe the Foata--Schuetzenberger objects; this fixed-object task is qtBench-proposed. | Large probes spread across descent counts and extreme/random admissible descent sets; enumeration of `Gamma_{n,k}` is exponential, while scalable rank formulas remain a semantic risk. Reviewer judgment remains necessary. |
| 18 | **High generic risk only:** the public `u=1` eta-graded marginal constrains the missing statistic, but no scalable target formula is documented. | Full eta/`u`/`t` coefficients are checked. Large minimal and random tall gamma-parking selections vary `gamma`, content, and selected cells. |
| 19 | **High generic risk only:** no problem-specific shortcut is documented for the rooted-tiered-tree Theta target. | Exact joint targets plus one-tier, two-tier, fully tiered, and random large rooted trees. The root model differs from problem `9`, preventing a trivial reuse that ignores root compatibility. |
| 20 | **High generic risk only:** this has the same generic risks as `18`, with an additional global lattice-word constraint. | The full eta-graded target is checked, and the large generator constructs valid lattice-word probes rather than reusing the ordinary family unchanged. |
| 21 | **High generic risk with a strong resource lever:** the target has no known scalable q,t-Ehrhart formula, and the requested statistic must use the graph as well as the tree. | Full graph-indexed joint targets are checked. Large probes cover star, complete, intermediate threshold graphs, random trees, and a deepest path. A graph-ignoring rule may pass isolated samples but has no known all-case bypass. |
| 22 | **Critical confirmed bypass (`ACTION-1`):** promotion-orbit position reproduces the target by definition and passes the lower-level evaluator cheaply. | The active item receives the ordinary automatic score; subsequent semantic review must distinguish an intrinsic statistic. The passing reproducer records the residual mechanical limitation. |
| 23 | **High residual (`RANK-1`) and source-status caveat:** the Reiner--Sommers target has a closed formula, but no source was located posing the objectwise statistic question. | The item is labelled a qtBench-proposed natural-statistic challenge. Exact polynomial and large-probe checks remain diagnostic, not evidence that the source posed the challenge. |
| 24 | **Critical residual (`BIJ-2`):** uniform rank matching across conjugate-shape `(inv,maj)` fibers would pass without explaining Macdonald symmetry. Known hook solutions are excluded, so patching only that family is insufficient. | Complete non-hook public fillings plus large non-hook shapes receive canonicality, conjugate-shape, two-round-trip, and both pointwise exchange checks. |
| 25 | **Critical residual (`BIJ-2`):** rank matching inside equinumerous parking-function `(area,dinv)` bags would assume the diagonal-coinvariant symmetry. | Complete public sizes and large varied parking functions receive validity, size, both round trips, and both exchange checks. The one-variable zeta map does not satisfy these gates. |
| 26 | **High specific probe-recognition risk (`PROBE-1`), proved by inspection:** exact general graph checking is capped at seven vertices, which is also the public maximum; genuinely large checks are star/complete pairs whose images are uniquely forced and recognizable. | The earlier all-small collapse is fixed by three large star/complete scales, the only probes above the public range. The randomized graphs alongside them stay inside the exhaustive public enumeration and add no size coverage. A branch that special-cases the extremes remains possible, while arbitrary large canonical graph outputs cannot be validated economically. |
| 27 | **High residual (`RANK-1`):** the DPP target is public through an exact product/enumerator, but no scalable ASM rank assignment is established. A statistic can exploit public ASM features without being mathematically illuminating. | The complete public ASM distribution is exact; capped resource orders 64, 128, and 256 include permutation and non-permutation ASMs without exceeding the shared memory envelope. Enumeration faces the resource gate; there is no integer-magnitude gate. |
| 28 | **Critical residual (`BIJ-2`):** rank matching by full content between the signed shifted-tableau unions would prove no explicit Chiu--Marberg map. | Both public sides are exhaustive. Resource orders 256, 512, and 1,024 provide distinct valid Q/P scales, with no duplicated maximum, and check canonicality, correct side, complete content, and both round trips; direct enumeration is uneconomic, but a uniform matcher remains semantically irreducible. |
| 29 | **Critical residual (`BIJ-2`):** weight-by-weight rank matching can use the analytic Andrews--Bressoud equality without giving its requested bijective proof. | Public source and target sides are exhaustive. Large structured and seeded-random probes span all four public `(M,r)` pairs and check side, unchanged parameters and weight, canonicality, and both round trips. Public-only tables fail; a scalable uniform matcher cannot be classified mechanically. |
| 30 | **Critical residual (`BIJ-2`):** grading-wise rank matching between improper partition matrices and restricted inversion sequences would satisfy the observable identities without explaining Chern--Fu's map. | Both public sides are exhaustive. Large deterministic and random objects check side, size, grading, canonicality, and both round trips. A uniform semantic shortcut remains irreducible. |

## Benchmark interpretation risks, not checker bypasses

These issues affect how a score should be reported. They do not cause a
numerically wrong submission to pass.

### Solved calibration (`1`)

Problem `1` deliberately publishes a known-good statistic. It is useful for
testing submission packaging and admission behavior, but including it in a
discovery success rate would inflate that rate. Its presence is not target
leakage: it is explicitly labelled and the evaluator is behaving correctly.

### Conditional committed target (`3`)

The last three type B targets are conditional reconstructions under the stated
SL2-string and specialization assumptions. Exact checker agreement proves
agreement with those committed polynomials. It cannot upgrade their provenance
to an unconditional theorem. Moreover, the repository contains neither the raw
direct-computation work for `n=5,6` nor the reconstruction program and raw solver
records for `n=7,8,9`; `generate_data.py` only re-emits the committed targets and
checks basic invariants. Reports should preserve both qualifiers.

### Public targets and generation material

All scored polynomial coefficients are public, and derivation oracles are
public except for the documented Problem 3 provenance gap above. This is
intentional: target secrecy is not part of the threat model. The scored
evaluator does not load an oracle, and CAP-1 blocks a submission from reading
one at runtime. A submitter may still study or copy
public formulas; source economy, resource probes, and reviewer judgment address
what follows from that access.

### Sample instances versus the scored range (most problems)

`data/instances.json` is usually a small orientation sample. The scored range is
in `metadata.json` and `data/polynomials.json` and is larger for nearly every
problem. Fitting the sample is not an attack on the checker: it fails when the
complete public enumeration is compared. Confusing the two is a validation
error by the submitter or reviewer.

### Known anchors and solved subfamilies

Several open problems include solved fibers or classical specializations. They
are valuable correctness anchors, but a program assembled from those answers
is not a full pass unless combined with another mechanism for the unsolved
cases. Conversely, a passing distribution on an anchor does not necessarily
establish the intended objectwise equality; that separate issue is `ANCHOR-1`.

## Detailed entries

### CAP-1 — External capability

A submission attempts to read public targets at runtime, load a generation oracle,
import a solver, use reflection, start another process, or communicate over the
network. The scored path admits only a small Python subset and installs an audit
hook in each worker.

The screen also rejects every direct attribute store or delete. Those operations
provided a route for state to outlive a namespace: the helper functions injected
into each submission namespace are module-level objects shared by the whole
process, so `helper.stash = ...` in the first pass was readable from the "fresh"
replay namespace, breaking the isolation required by STATE-1. The rule also
blocks direct writes such as `object.cache = value`. It does not block item
assignment or a mutating method call on a mutable value read from an input
attribute; the checker therefore makes no general input-immutability claim.
Regression tests for the direct-write rule are
`test_capability_screen_rejects_attribute_writes` and
`test_helper_attributes_cannot_carry_state_between_namespaces`.

The screen once inspected `def` and not `lambda`, which are equally ways to bind
a callable. The signature rule was the smaller half: `statistic = lambda p,
cache={}: ...` was admitted where the `def` spelling was rejected. `visit_Lambda`
now applies that rule at every nesting depth. Its false-rejection cost is the
late-binding idiom `[lambda x, i=i: x + i for i in range(3)]`, which the `def`
rule has always excluded and which a statistic does not need.

The trusted-name check had a wider version of the same gap. It read top-level
`def` names only, so `sum = lambda values: 0`, its annotated, unpacked and
loop-target spellings, a `def` nested in a module-level `if`, and a plain alias
`sum = helper` all kept a whitelisted builtin's name. That is not inert:
`visit_Call` admits a call to any whitelisted name, and the module binding
shadows the builtin, so the submission's own `sum(...)` reached the binding. The
check now reads `def` names together with the `Store` targets and `global`
declarations that bind at module scope. Function and comprehension bodies keep
their own scope, so a local `sum = 0` is untouched, and `except E as name` is
excluded because Python deletes that name when the handler exits.

Two constructs bind at module scope from inside a nested one: an assignment
expression in a comprehension, and a `match` capture pattern, whose name is a
plain string rather than a `Store` target. Enumerating those spellings failed
twice, so the screen now rejects `:=` and `match` outright. That is a syntactic
rule rather than a necessary property of a statistic, so its false-rejection
cost is accepted here explicitly: neither construct is needed to express one,
and what remains is a rule short enough to state completely. None of these gaps
was a route to a score, because every evaluator requires its entry point among
the screened top-level `def` names. Regression tests:
`test_capability_safety_blocks_escapes_and_dynamic_signatures`,
`test_capability_safety_blocks_shadowing_trusted_names` and
`test_capability_screen_rejects_walrus_and_match`.

Residual risk is an implementation or interpreter escape. The capability screen
is a narrow execution boundary, not a formal operating-system sandbox.

### EMB-1 — Embedded answer

The target assignment is represented directly in source literals or reconstructed
from a compressed constant. Byte, line, token, AST-node, and literal-byte limits
make ordinary tables infeasible. Compact formulas and generated tables remain
possible and may overlap legitimate mathematics.

### STATE-1 — Stateful or order-dependent assignment

The submitted statistic or bijection hands out outputs according to enumeration order,
or returns a special answer only on an object's first call. Such code may match a
bag-level polynomial without defining a function of the object.

The checker evaluates the public target first, then reloads the submission in a
fresh namespace, evaluates each public fiber in a secret single-cycle shuffled
order, and repeats every submitted callable. A keyed order-independent
fingerprint requires the function/object/output assignment to agree between the
two namespaces. This includes `forward` and `inverse` for bijections, which are
recorded and replayed exactly like a statistic. Because every position lies in
one permutation cycle, a nonconstant value-by-position schedule cannot preserve
the same assignment accidentally.

For bijections the earlier numerical stage is already order-hardened on its own:
checking `inverse(forward(p)) == p` and `forward(inverse(p)) == p` calls each
direction more than once per public object, so a first-call-only map fails the
round trip before the replay stage is reached.

It does not reject deterministic object-based rank assignment; that is RANK-1.

### MARG-1 — Marginal-only fitting

A proposal matches `data/q_equals_1.json` (or the `u = 1` file for problems
`18` and `20`) but ignores how its output couples to the public statistic. For
example, on a q,t-statistic problem it can hand out the correct multiset of
`t`-values while assigning those values to the wrong `area` fibers.

This is blocked: statistic adapters compute the marginal and the complete joint
polynomial from the same enumeration pass, and a marginal-only match stops at
the numerical stage. Problem `12` checks the full trivariate distribution, and
problems `8`, `18`, and `20` retain their partition grading in the full target.

The marginal's evidentiary value varies:

- it genuinely constrains the submitted output on the ordinary q,t tasks,
  problem `13`, and the composition-valued problem `8`;
- on problems `14`--`17`, `22`, `23`, and `27`, it is only a shape/fiber/object
  count that the submitted exponent cannot change;
- for bijections it is redundant once the complete pointwise identities and
  distribution hold.

That variation is not a bypass because the full target is always mandatory. It
is a reporting hazard: “passed q=1” must never be summarized as “nearly passed.”

### ANCHOR-1 — Pointwise-anchor permutation

An exact generating function sees only a multiset of outputs inside each public
fiber. If the mathematical statement also specifies which individual objects
must receive particular values, those values can be permuted among objects
without changing any coefficient.

Concrete open examples in the current bank are:

- problem `13`: the classical `mu=(n)` and `mu=(1^n)` anchors state `maj(T)` and
  zero objectwise;
- problem `14`: the complete-graph anchor states `lltstat_{K_n}(T)=maj(T)`;
- problem `15`: the fixed-point-free anchor states
  `istat(pi)=(n-lds(pi))/2`;

Problem `16` previously admitted a concrete version: take two objects in the
same `(lambda,pi,sigma)` fiber, one
bipartite with intended value `0` and one non-bipartite with intended value
`d>0`. Swapping their values leaves `c^lambda_{pi,sigma}(q)` unchanged but
destroys the marker-of-non-bipartiteness condition. The checker now rejects this
swap both on complete public fibers and on large resource probes.

Some anchors are already forced by singleton support: the identity involution,
the LLT row/column tableaux, and the two extreme noncrossing block types leave
no object with which to swap. The non-singleton anchors above are not. Unlike
the general question “is this statistic natural?”, these pointwise statements
could be added as explicit problem-level gates without using a heuristic. Until
then, reviewers must verify them from source. This entry is proved by inspection
of the numerical adapters and resource-result validators; it is not presented
as a separately implemented all-gates submission.

### CUTOFF-1 — Public-range fitting

The proposal is correct on the exact public parameter range and returns any
valid small output beyond it. A large resource gate cannot detect this for an
unknown statistic because it has no large-object ground truth.

More exact cases increase the fitting cost but do not remove the attack. Output
diversity, smoothness, or runtime-shape requirements are not universal
properties of meaningful statistics and therefore are not safe generic gates.

This is most acute for the 21 statistic tasks. Their large probes generally have
no target ground truth, so they validate output type and resource use. Problem
`16` has the stronger exact bipartite zero-locus guard, but values away from zero
remain unknown; a cutoff branch can still return `0` on bipartite probes and any
positive integer on the rest. The bijection tasks are better protected: on large
objects the defining side/shape, round-trip, statistic, content, weight, or
grading identities are self-checking. They still have a finite-probe variant of
the risk through `PROBE-1`.

Known subfamilies make patchwork submissions cheaper without completing them.
Examples include the solved calibration problem `1`; the classical or published
anchors in `13`--`17` and `22`; the hook-shape results excluded from `24`; and
the `M=5` Rogers--Ramanujan cases excluded from `29`. A patch over such families
must still explain every remaining public case, so this is an attack ingredient,
not a confirmed pass by itself.

### ENUM-1 — Exhaustive search

The proposal enumerates an exponentially large object family for each input,
then locates the input or assigns a target value. Random large objects under
time and memory limits reject the straightforward form.

This does not cover polynomial-time dynamic programming or ranking.

### RANK-1 — Uniform rank assignment

For each public-statistic fiber, the proposal canonically ranks the input and
uses cumulative target coefficients to assign the missing exponent. If counting
and ranking the family are polynomial-time, this is a pure, deterministic,
uniform, polynomial-time function with the exact target distribution at every
size.

No black-box correctness, determinism, resource, or random-probe test can
distinguish this construction from a meaningful statistic. Rejecting it requires
additional mathematical structure or semantic judgment.

Two independent computations are needed: rank the object in the relevant
fiber, and obtain the target coefficient boundaries. Public target data makes
both cheap on the scored range; the large probes ask whether they scale.
Repository documentation supports the following finer assessment:

- problem `17` has a short recurrence and problem `23` has a closed formula, so
  target recomputation itself is not the main obstacle;
- problems `8`, `13`--`16`, and `18`--`21` require the same hard basis change,
  elimination, or q,t-Ehrhart computation that motivates the problem, so no
  scalable target recomputation is known;
- problem `22` bypasses this question entirely through `ACTION-1`;
- problem `27` publishes a product/enumerator for the DPP target, but this file
  makes no claim that coefficient extraction plus ASM ranking fits the probe
  budget.

These are threat assessments, not complexity theorems. In particular, “closed
target” does not imply “confirmed passing ranker”: the object-ranking half can
still require exponential enumeration. Large integers alone are no longer rejected.

### ACTION-1 — Recomputing the defining action

When a target is *defined* from a group action rather than merely satisfied by
one, the definition itself is a passing submission. The instance in this
repository is problem `22`: the cyclic sieving polynomial `C_lambda(q)` is built
by grouping `SYT(lambda)` into promotion orbits and summing
`1 + q^{N/|O|} + ... + q^{(|O|-1)N/|O|}` per orbit, so a proposal that walks an
object's orbit, takes its lexicographically least element as the origin and
returns the step count times `N / |O|` reproduces every public target exactly.

Unlike RANK-1, this attack needs no target data, only the public action. It is
also inexpensive: promotion is `O(rows + columns)`, so a full orbit walk on a
`990`-cell staircase takes about `0.1` seconds, well inside the resource budget,
and the cost grows only like `n^{3/2}`. Enlarging the probes therefore does not
help. A submission that combines this with the published answer on the solved
sub-family passes every stage of the lower-level evaluator; this has been
verified. The public CLI also permits an automatic mechanical pass; it does not
certify that the statistic is intrinsic.

Two consequences follow. First, distribution checks cannot help: the construction
and intended statistic agree in distribution on every fiber and differ only
pointwise, which is precisely what the checker does not compare. Second, a solved
sub-family of the kind that anchors problems `15`, `17` and `22` constrains
correctness but cannot exclude a construction that is already correct -- an earlier version of
problem `22` claimed otherwise and was wrong.

The mitigation is subsequent semantic review by a judge or expert. It is not a
mechanically enforced guarantee. The defining action is not exposed on
the objects, which makes the construction conspicuous in source, and
`problem.md` states outright why a lower-level evaluator pass is not evidence of
an answer. This limitation should be considered before
another problem whose target is defined from an action is added. The benchmark
issues an automatic mechanical score, while mathematical acceptance requires
review. The [inference scaffold](../../inference/README.md) provides that
checker-before-judge workflow.

### HARNESS-1 — Inference broker and process-boundary escape

Scaffold review confirmed three harness attacks during development;
none was a bypass of the released scored checker. A solver-controlled file path
could redirect a naive host broker through a symlink or FIFO, a forged or
replayed response could mislead a client that failed to bind all request fields,
and a background process that changed session could outlive a process-group
timeout. The integrated scaffold holds pre-opened request and response directory
descriptors, accepts only bounded no-follow single-link regular files, writes
responses atomically, and binds each client response to the request ID,
submission ID, and exact source hash. Host success comes only from the in-memory
judge/checker result, never from a workspace response file. One absolute
wall-clock deadline covers the full run, and every solver, judge, and checker
tree runs under a dedicated Linux subreaper that kills and reaps detached
descendants. The live preflight fails closed unless filesystem/network
sandboxing, a private sandbox PID namespace, protected control paths, and
detached-child cleanup all succeed.

Focused regressions live in `inference/tests/test_protocol.py` and
`inference/tests/test_sandbox.py`. These controls preserve host integrity and
resource bounds; they cannot make the semantic judge infallible. Solver-authored
prompt injection and solver self-denial remain review limitations documented in
the [inference guide](../../inference/README.md).

### TARGET-1 — Target-directory substitution

An earlier scored CLI accepted `--problem-dir` and passed that directory directly
to the evaluator selected by `kind`. A caller controlling scorer arguments could
therefore supply compatible attacker-chosen metadata and targets, obtain a pass
against them, and bypass the committed benchmark data without escaping the Python
submission sandbox.

The scored CLI now maps each `kind` only to its registry-backed directory and
rejects the override. The separate unscored inspection utility still accepts an
explicit problem directory by design; it does not issue an admission result. This
fix binds the public scored entry point, but cannot constrain a downstream system
that bypasses it and invokes lower-level evaluators with untrusted target paths.

### IPC-1 — Parent-side result expansion

Checker version 13 attempted to materialize arbitrary iterable types as the
composition-valued output for problem `8`. A compact `range(n, n + 1)` therefore
passed the large-output type gate despite violating the documented tuple/list
contract, while a much larger compact range could be expanded by `tuple(value)`
in the scorer parent outside the worker resource limits after crossing the
bounded worker IPC channel. The first mechanism could also leave an
unserializable raw range in the official result; the second was an
availability/OOM risk. Both require a submission that has already passed the
exact public numerical stage and are not evidence of a target-polynomial bypass.

Version 14 accepts only exact built-in tuples or lists, bounds their length by
the object size before copying, and bounds every positive part before summing.
Composition-validation error paths never render the submitted value or invoke
iteration on a non-exact container. Version 15 additionally keeps each
worker-generated message encoded until the worker has exited successfully and
checks the parent reserve after deserialization. The 8 MB message still uses a
pickle wire format whose object graph is submission-influenced; replacing that
format remains a separate defense-in-depth opportunity.

### MEM-1 — Aggregate process-envelope exhaustion

Through checker version 14, official configuration gave one worker a
256,000,000-byte process ceiling but did not budget the evaluator parent. That
left only 12,435,456 bytes below a 256 MiB external envelope for the interpreter,
target data, IPC payload, and decoded result together. A worker staying within
its individual limit could therefore make an external aggregate memory limit
terminate the scorer. This was a confirmed accounting gap and an availability
risk, not a demonstrated way to manufacture a passing receipt.

Checker versions 15–17 and official scoring configurations v2–v3 cap a worker at
201,326,592 bytes (192 MiB), reserve 67,108,864 bytes (64 MiB) for the evaluator
parent, and cap their sampled sum at 268,435,456 bytes (256 MiB). Before creating
each worker, the scorer requires the two configured caps to fit the aggregate
budget and the current parent RSS plus the maximum 8,000,000-byte IPC message to
fit the parent reserve. While a worker is live, RSS measurement failure, either
individual-cap violation, or aggregate-cap violation rejects the run. IPC
headroom is rechecked after every pipe poll and before `recv_bytes`; after the
receive, the actual parent/worker sum is checked again. The parent keeps those
bytes encoded, confirms clean worker exit, then deserializes and checks the
parent reserve again; both encoded and decoded payload are resident for that
final check.

The current statistic v3/bijection v4/checker-18 values are asserted in
successful, gate-error, and promotion numerical-failure receipts by
`test_scored_main_records_provenance_and_replaces_inherited_seed_overrides`,
`test_cli_rejects_oversized_source_before_reading_it`, and
`test_cli_scores_promotion`.

The aggregate context is activated by the official scored CLI only. Direct
lower-level evaluator calls retain their caller-selected per-process contract
and do not claim this aggregate envelope. RSS polling is sampled rather than an
operating-system cgroup, and the context does not claim a whole-process
high-water bound for later trusted JSON/report rendering. Those are residual
availability limitations, not known score-verdict bypasses.

### INT-1, INT-2, INT-3, INT-4, INT-5 — Integer representations

Checker version 18 removed the intermediate integer-magnitude audit. Large
built-in integers, ephemeral values, and limb encodings face only the unchanged
source, time, and memory limits. The previous bounded scan and profile callback
are historical; INT-4 and INT-5 are retired. An integer of magnitude `2**n`
needs only `O(n)` bits, so memory limits alone cannot exclude it.

### PROBE-1 — Probe recognition

The proposal recognizes fixed examples or deterministic adversarial shapes and
special-cases them. Resource probes include extremal objects plus randomness
chosen after submission, at several sizes. Exact probe hardcoding is therefore
fragile.

A size-only cutoff remains possible; see CUTOFF-1.

Problem `26` previously collapsed every nominal large probe to at most eight
vertices, so a branch at the public maximum of seven defeated its resource
gate. `test_adversarial_connected_graphs_include_large_extreme_pairs` pins the
mitigation: star/complete pairs at three genuinely large sizes, whose exchange
images are uniquely forced. Those pairs are the whole of the coverage above the
public range. The general graphs in the same probe set are capped at seven
vertices -- a path, a cycle, and one seeded random graph -- and the public range
already enumerates every connected graph up to that size, so all three re-check
published objects rather than extending the range. Validating an arbitrary large
graph would need general canonical labeling, which does not fit the budget.
Recognizing and special-casing the extreme shapes therefore remains an instance
of this irreducible probe-recognition limitation, and problem `26` gets less
from the post-submission randomness described above than the other problems do.

### TYPE-1 — Degenerate large output

The proposal returns correct values publicly but uses invalid placeholders on
large probes. Every large statistic result is checked for the declared exact
type: a nonnegative `int`, or a valid composition for the unit-interval-graph
task.

Valid but meaningless placeholders such as zero remain CUTOFF-1. For problem
`16`, zero is valid only on bipartite large probes and a positive placeholder is
required on non-bipartite probes.

### BIJ-1 and BIJ-2 — Bijection fitting

Finite tables and exhaustive public-size bijections are checked again on large
random objects for validity, round trips, and pointwise statistic identities.
This makes bijection resource gates stronger than statistic resource gates.

A uniform rank-matched bijection between equinumerous fibers satisfies the same
identities on every object. Its lack of combinatorial meaning is not mechanically
observable.

The rank fiber depends on the task:

- `(area,bounce)` within one set for `2` and `4`, or across transposed boxes for
  `5`;
- `(inv,maj)` across conjugate filling shapes for `24`;
- `(area,dinv)` on parking functions for `25`;
- `(reduction,sibling,tuft)` on connected graphs for `26`;
- full tableau content and side for `28`;
- `(M,r,weight)` for `29`;
- `(n,grading)` for `30`.

The large gates recompute precisely those pointwise identities, including both
directions of the round trip. This is stronger than the statistic resource gate:
returning zero or another valid placeholder is not enough. It still cannot tell
whether the submitted algorithm gives a structural map or merely ranks both
sides of an equality already known analytically.

Problems `29` and `30` therefore disclose rank matching as an irreducible finite
bypass. Their large gates add scalable extreme pairs on both sides and verify
canonicality, side membership, grading, and both round trips, which blocks a
literal public table or exhaustive enumerator but cannot recognize whether a
uniform formula is mathematically enlightening.

### DIAG-1 — Unrestricted diagnostic execution

`scripts/evaluate/evaluate_submission.py`, `evaluate_submission_file`,
`load_statistic_function`, and the trusted-oracle loaders used by the problem
`1` and `6`--`23` generation and certification tooling intentionally import and
execute supplied Python as an ordinary module in the caller's process. Problem
`1` also accepts an explicit, potentially non-adjacent `--statistic-module`
path. That gives top-level code the
caller's file, network, process, environment, and credential access, with no
checker timeout or memory boundary. Restoring a temporary module name does not
undo those effects, and output from an untrusted diagnostic run is itself
attacker-controlled.

This is not a checker escape: the official scored CLI executes submission source
only after capability screening, inside isolated workers. The diagnostic path
is for trusted local files only; evaluating untrusted code requires an external
operating-system sandbox. A diagnostic result is neither an admission verdict
nor a scoring receipt.

### EXPLOIT-1 — Checker escape

The attack targets the implementation rather than the mathematics: parser gaps,
unsafe attributes, audit-hook omissions, serialization behavior, or runtime
vulnerabilities. Reflective formatting is explicitly rejected and worker IPC is
bounded and serialized under the child limits, with focused regressions for both.
The remaining boundary is still not a formal operating-system sandbox. Every
confirmed escape should receive a focused regression test and an update here.
