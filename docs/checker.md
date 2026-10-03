# Submission checker

The checker in `qtbench.evaluation.admission` determines whether a proposal is
admitted. **Passing is necessary, never sufficient.** A genuine statistic or
bijection expressed within the public submission contract should pass, but so
can a polynomial-time construction that reads the answer from the known target
polynomial and assigns values by rank. No
executable test can distinguish them: the ranking construction is itself a
polynomial-time function of a single object (see *Why not more* below). The
checker therefore rejects the *cheap* cheats and enforces the strongest simple,
mechanical conditions available. It does not assess semantic or mathematical
authenticity.

A hard gate should enforce a necessary, clearly auditable property of a
submitted statistic or bijection. More opaque heuristics belong in the cheating
taxonomy unless their false-rejection tradeoff is explicitly accepted.

## Semantic integrity: gaming the checker is not a solution

qtBench is a mathematical-discovery benchmark. Its purpose is to find a
structural statistic or bijection that could explain an identity uniformly, not
just a program whose output agrees with the committed finite data. A candidate
is therefore not an acceptable solution when its rule is chosen primarily to
manufacture a good checker score, even if the program is short, pure,
deterministic, polynomial-time, and accepted by every mechanical stage.
Gaming the checker in this way is wrong: it violates qtBench's semantic
integrity requirement and must not be presented as mathematical progress.

This policy covers both direct cheating and the broader benchmark-gaming
behavior that a mechanical checker cannot reliably recognize. Unacceptable
strategies include:

- embedding or reconstructing target answers, assigning values by object rank
  or call order, matching source and target objects by enumeration rank, or
  recomputing the defining action that the requested construction is meant to
  explain;
- fitting only the public size range, recognizing known probes, returning a
  fallback outside that range, or adding literal public objects, exact
  parameter tuples, or named residual shapes as score-repair exceptions;
- using public checker distance as the objective for an expressive search over
  coefficients, edge or vertex orders, thresholds, chambers, case splits, or
  combinations of formulas, and then submitting the winner without an
  independent mathematical derivation;
- repeatedly mining the remaining coefficient errors and adding narrower
  branches whose only justification is that they close those errors; and
- exploiting checker behavior, configuration, resource probes, replay order,
  runtime capabilities, or mutable state instead of addressing the
  mathematical problem.

The third item matters even when every member of the searched family is a
well-defined statistic and preserves a theorem-backed marginal. A marginal
theorem does not make a joint statistic meaningful when its particular
parameters and case structure were selected chiefly by full-range score
optimization. Likewise, rewriting a fitted exception in structural-looking
language does not by itself make the construction explanatory.

Public targets and checker feedback may still be used as empirical evidence.
It is legitimate to test a small, mathematically motivated family, compare
conventions, diagnose implementation errors, investigate a known subfamily, or
reject a structural conjecture after it fails. Computation may also reveal a
pattern that leads to a new conjecture. Before that conjecture is treated as a
candidate solution, however, its rule and every material constant or branch
must have a reason that is independent of the finite score and must make a
genuine prediction beyond the residual cases from which it arose.

An exact exceptional case is not automatically gaming: singular parameters and
proved subfamilies can be mathematically essential. The burden is to explain
the exception from the underlying objects or theory, state it as part of a
uniform family, and test consequences not used to select it. “This fixes the
last public fiber” is evidence of fit, not a mathematical justification.

A useful counterfactual is:

> If the checker, public coefficients, enumeration order, and scored-size
> boundary disappeared, would the same rule still be natural to state, would
> each branch still have a structural reason, and could the rule plausibly be
> the subject of a proof that does not assume the target identity?

If the answer is no, the candidate must not be reported as a qtBench solution.
Semantic review should identify it as cheating or benchmark-dependent gaming
regardless of numerical distance or automatic verdict. Disclosure is required
for auditability, but candidly describing a fitted mechanism does not make that
mechanism acceptable. Honest partial progress or a failed natural conjecture is
strictly preferable to a lower score obtained by gaming the finite benchmark.

The stable mechanical attack identifiers and their current mitigations are
recorded in the [cheating taxonomy](cheating/taxonomy.md). That catalog does
not exhaust this semantic policy: score-conditioned formula fitting can be
unacceptable even when it does not instantiate a mechanically recognizable
ranker, lookup table, cutoff, or exploit.

## Supported platform

The official scored CLI targets Linux and Windows, and the package requires
Python 3.11 or newer.
CI runs the complete suite on Python 3.13, compatibility smoke tests on Linux
with Python 3.11, 3.12, and 3.14, and targeted Windows jobs on the endpoint
versions 3.11 and 3.14. Linux adds kernel
resource limits to the portable wall-clock, RSS, and Python-allocation checks.
Windows measures RSS through `GetProcessMemoryInfo` and uses the same
parent-enforced deadline and allocation checks. macOS uses its `ps`-based RSS
fallback and is best-effort rather than an official scoring platform.

## Stages

A scored submission runs these stages in order; the first failure stops.

1. **Capability screen** — the source must be pure, self-contained Python: no
   imports, classes, reflection, dunder access, dynamic calls, or non-default
   argument forms. Assignment expressions and `match` are excluded too, because
   both bind a name outside the construct that spells them, and a submission may
   not reuse a whitelisted builtin's name for anything it binds. Reflective
   formatting calls are also excluded, and attributes may not be written or
   deleted. Blocking direct attribute writes prevents a submission from placing
   state on injected helpers shared by the replay namespaces in stage 4. It does
   not prevent every mutation through a mutable value obtained from an input
   attribute, so input immutability is not a mechanically enforced guarantee. A
   submission may call only a small whitelist of builtins, plus its own
   functions. The screen does not judge the algorithm; dicts, sets, recursion,
   and `while` loops are allowed.
   The process audit hook adds defense in depth, but this is not a formal
   operating-system sandbox.
2. **Source economy** — byte, line, token, AST-node, and literal-byte caps. A
   submission large enough to embed an answer table is rejected here.
3. **Public numerical correctness** — in a limited process, every public object
   is enumerated once. Statistic adapters compare both the public marginal and
   full target. Bijection adapters compare the full bivariate target and all
   pointwise identities; their marginal follows algebraically from the full
   equality. A mismatch stops here.
4. **Referential transparency** — a submission that passed numerically is loaded
   again in a fresh namespace. Within each public fiber, objects are evaluated in
   a secret single-cycle shuffled order and every submitted callable is repeated.
   A keyed, order-independent fingerprint of `(function, object, output)` records
   must match the first pass. This applies equally to statistics and to both
   directions of a bijection. It rejects call-order schedules, first-call
   behavior, and mutable global assignments while allowing deterministic
   memoization.
5. **Resource gate** — on large adversarial objects (default requested size
   1024) under
   CPU, wall-clock, and memory limits. Statistic outputs must still have the
   declared type on these probes. Problem `16` additionally enforces the exact
   Matchings-Jack zero locus pointwise: the submitted value is zero if and only
   if the large matching is bipartite. Enumerating the object set is exponential
   and cannot fit the budget. For every bijection problem this stage also checks
   the required identities pointwise on each large object; the identities are
   self-checking, so large-object correctness is verified with no target.
   Worker-to-parent messages are capped at 8 MB and serialized inside the limited
   worker. Official scoring assigns a 192 MiB worker ceiling, a 64 MiB reserve
   for the evaluator parent and its encoded/decoded payload, and a sampled
   256 MiB aggregate envelope. The parent reserve includes space for the maximum
   IPC message and is rechecked before every receive. The payload remains encoded
   until worker exit is confirmed. The Python-allocation limit applies to the
   submission-only resource probes, including module initialization; numerical
   evaluation uses the worker process limit because its `tracemalloc` total also
   includes trusted enumeration and comparison data. Composition-validation
   error reporting never renders an
   unvalidated container, and a validator never invokes the iteration protocol
   on a non-exact container.
   Composition results must be exact built-in tuples or lists of at most `n`
   parts before any bounded copy, so compact iterables cannot expand outside the
   worker limits. Accepted integer results, including
   both components of a pair, must also be available to the runtime's decimal
   converter used by the official JSON encoder. An integer beyond that runtime
   digit limit is rejected inside the resource-result validator, before report
   rendering.

   Problem `26` caps its general canonical probes at seven vertices, which is
   also its public maximum, and adds star/complete pairs at the requested large
   sizes. Those two graphs have uniquely forced exchange images, so the checker
   can validate large outputs exactly without solving general graph canonical
   labeling at size 1024; they are also its only probes above the public range.

   Problem `27` caps its underlying probe order at 256 so dense ASM rows stay
   inside the same 32 MB traced, 192 MiB worker, and 256 MiB aggregate
   envelopes; its effective resource orders are 64, 128, and 256. The linear-size
   shifted P/Q objects in problem `28` use orders 256, 512, and 1024. That gate
   reuses the supplied maximum-order objects and generates only the two lower
   orders, rather than duplicating the maximum.

Run it with the appropriate evaluator kind below. Every listed kind, including
`promotion`, receives the ordinary automatic mechanical score.

```bash
uv run --locked python scripts/evaluate/evaluate_scored_submission.py noncrossing submission.py
uv run --locked python scripts/evaluate/evaluate_scored_submission.py type-b submission.py
uv run --locked python scripts/evaluate/evaluate_scored_submission.py lpp submission.py
uv run --locked python scripts/evaluate/evaluate_scored_submission.py ddyck submission.py
uv run --locked python scripts/evaluate/evaluate_scored_submission.py ttree submission.py
uv run --locked python scripts/evaluate/evaluate_scored_submission.py mld submission.py
uv run --locked python scripts/evaluate/evaluate_scored_submission.py lrp submission.py
uv run --locked python scripts/evaluate/evaluate_scored_submission.py tamari submission.py
uv run --locked python scripts/evaluate/evaluate_scored_submission.py gpf submission.py
uv run --locked python scripts/evaluate/evaluate_scored_submission.py rtt submission.py
uv run --locked python scripts/evaluate/evaluate_scored_submission.py lgpf submission.py
uv run --locked python scripts/evaluate/evaluate_scored_submission.py tgt submission.py
uv run --locked python scripts/evaluate/evaluate_scored_submission.py kostka submission.py
uv run --locked python scripts/evaluate/evaluate_scored_submission.py uig submission.py
uv run --locked python scripts/evaluate/evaluate_scored_submission.py llt submission.py
uv run --locked python scripts/evaluate/evaluate_scored_submission.py involution submission.py
uv run --locked python scripts/evaluate/evaluate_scored_submission.py mjack submission.py
uv run --locked python scripts/evaluate/evaluate_scored_submission.py qgamma submission.py
uv run --locked python scripts/evaluate/evaluate_scored_submission.py promotion submission.py
uv run --locked python scripts/evaluate/evaluate_scored_submission.py kreweras submission.py
uv run --locked python scripts/evaluate/evaluate_scored_submission.py area-bounce submission.py
uv run --locked python scripts/evaluate/evaluate_scored_submission.py polyomino-area-bounce submission.py
uv run --locked python scripts/evaluate/evaluate_scored_submission.py polyomino-transpose submission.py
uv run --locked python scripts/evaluate/evaluate_scored_submission.py macdonald-fillings submission.py
uv run --locked python scripts/evaluate/evaluate_scored_submission.py parking-area-dinv submission.py
uv run --locked python scripts/evaluate/evaluate_scored_submission.py graph-sibling-tuft submission.py
uv run --locked python scripts/evaluate/evaluate_scored_submission.py asm-q submission.py
uv run --locked python scripts/evaluate/evaluate_scored_submission.py shifted-pq submission.py
uv run --locked python scripts/evaluate/evaluate_scored_submission.py successive-rank submission.py
uv run --locked python scripts/evaluate/evaluate_scored_submission.py partition-matrix-inversion submission.py
```

Each command prints a short report by default; `--format json` emits the
complete machine-readable result, with one record per public case.

Official scoring uses the source-defined configuration reported in every result
as `scoring_config`: requested probe size 1,024 (subject to the documented
problem `26` and `27` exceptions above), a two-second probe timeout, a
60-second statistic numerical timeout and a 480-second bijection numerical
timeout, 32 MB of traced Python allocation on adversarial resource and
identity probes, a 192 MiB worker-process ceiling (also used as the traced
allocation ceiling during statistic numerical/replay stages), a 64 MiB
evaluator-parent reserve, and a 256 MiB aggregate process envelope. Before each
official worker starts, the current parent RSS plus the maximum 8 MB IPC message
must fit the parent reserve and the configured worker/parent caps must fit the
aggregate envelope. The IPC headroom is checked again before receiving each
worker result; RSS measurement failures reject the run. Bijection numerical
evaluation does not trace individual Python allocations; its worker remains
subject to the process memory ceiling, and its `numerical_peak_python_bytes`
field is `null`. The 480-second limit was calibrated with the exact shareable
Problem 5 submission (SHA-256
`13962f095d03f4fc6bd5f762ddbc463cbb1c2098a5e91792f913c818ed0bf64f`)
over the complete 91-box public battery, which contains 1,033,411 polyominoes.
The numerical check and fresh shuffled replay took 218.5 seconds on the
calibration Mac, so the limit is about 2.2 times that measured runtime. Timings
are hardware-specific. An independent official-platform run at commit
`1349bcb41fd55ab7f6e4f26adb75ef411b270e83` on Linux with Python 3.12.3 and an
Intel Core i9-14900K took 214.9 seconds for numerical evaluation and replay
(215.6 seconds total wall time) and passed all 91 cases. The scored CLI accepts
no overrides for these values. It also chooses and reports a fresh `run_seed`
and ignores inherited run/replay seed environment variables, so a caller cannot
select recognizable probes or replay order. The unrestricted
`evaluate_submission.py` command is available only for non-scoring Problem 1
public-data diagnostics and rejects other problem directories. It imports the
submission in the caller's process with the caller's privileges and no checker
resource boundary. Use it only for trusted local files, or place it in an
external operating-system sandbox. Its output is not an admission verdict or
receipt.

Official JSON records a mechanical verdict, not mathematical acceptance.
Problem `22` uses the ordinary boolean `automatic_verdict`, with
`expert_review_required=false`; this field indicates the absence of a CLI status
gate, not exemption from subsequent semantic review. The reserved review-only
outcome remains available for problems without automatic scoring.
`automatic_verdict` is `true` or `false` only when the automatic scorer issues
a verdict. For an expert-review problem it is `null`,
`expert_review_required` is `true`, and `checker_stage` is `expert_review`;
this outcome must not be counted as an automatic failure.

The JSON result also records an informational provenance receipt: the public
problem ID, name, and evaluator kind; a SHA-256 over the selected problem's
`metadata.json` and `data/` bundle; the exact submission SHA-256 once source
ingestion succeeds; and (when Git is available) the checkout's HEAD commit and
working-tree dirty state, including untracked files.
Fields that cannot be established before an early gate failure are
`null`. These fields help detect accidental
result/artifact mixups; they are not a signature or remote attestation. An
official result still assumes a trusted Python interpreter and launcher, an
unmodified checker process, and a stable trusted checkout while hashing and
evaluation run. A caller who controls that trusted computing base can forge both
the verdict and every JSON field, so an external scoring service must invoke the
checker itself and retain the receipt rather than accept submitter-produced JSON
as proof.

## What the stages buy

Together, the stages establish that a passing submission is short, pure,
capability screened, correct on every public size, repeatable as a function of
each public object, and within the fixed, reported time and memory budgets on the
sampled large objects. This rules out many easy cheats: direct capability
escapes, literal answer tables, stateful bag assignment, and straightforward
runtime enumeration of the object set. Finite probes do not prove an asymptotic
complexity bound or reject big integers solely for their magnitude.

## Why not more

For several current problems, the relevant object fibers can be counted in
polynomial time and the target has a closed form. In those cases, a proposal can
compute an object's rank inside its fiber and read off the matching target value
in polynomial time. This is a legitimate local function, so no resource or
correctness check can distinguish it from a natural statistic. Other problems
have no efficiently known target formula; for them target recomputation may be
the dominant obstruction.

The checker does not inspect intermediate integer magnitudes. A scalable
counting or ranking construction can pass its mechanical gates; semantic review
remains necessary.

Referential transparency is narrower and stronger: being a statistic requires
the same object to have the same value independently of call history. The
checker establishes this over the complete public range with two fresh
submission namespaces, a secret single-cycle shuffled replay, repeated calls,
and a keyed fingerprint. It does not reject a deterministic object-based rank
assignment, because that construction really is a function.

The rigorous lever is problem choice: for a problem whose fiber counting is
genuinely hard, the ranking cheat becomes exponential and the resource gate is
decisive again. Assess this per problem.

Problem `13` (modified (q,t)-Kostka) is where that lever is currently strongest.
Its fiber `SYT(lambda)` is easy to count, but the ranking cheat also needs the
target `K~_{lambda mu}(q,t)` itself. Algebraic formulas and finite computations
for that target are known; the open problem is a direct statistic pair on the
tableaux. The public route expands `H~_mu` and converts to the Schur basis, which
does not scale to the size-1024 resource probes within the checker budget.

Problems `17` (`q`-Eulerian gamma) and `23` (`q`-Kreweras) are the opposite case.
As their `problem.md` files explain, both targets have closed forms, so they are
cheap to recompute at any size; the gate only rules out enumerating the fiber.

For problem `22` (promotion cyclic sieving), the checker **cannot
distinguish a genuine answer from the known shortcut**. It uses the ordinary
automatic pipeline and active registry status; subsequent semantic review must
identify this shortcut. This limitation should be considered carefully
before another problem of its kind is added. Its target is *defined* from the orbits of a group
action, so "walk the object's orbit and return its position in it" reproduces
every public target exactly, with no mathematical content. Nothing in the
numerical stage can see the difference: the checker compares distributions, and
that construction has the right distribution in every case. This includes cases
where a theorem gives the intended answer, since the two agree in distribution
and differ only pointwise. Cost does not help either. Promotion is
`O(rows + columns)`, so a full orbit walk at `990` cells takes about `0.1`
seconds against a `2`-second budget, and the cost grows only like `n^{3/2}`. A
submission combining that with the published rectangular answer passes every
mechanical stage, including through the public CLI. The
[inference scaffold](../inference/README.md) invokes this checker first and
performs semantic assessment only after a passing checker result.

The broader lesson is that **when a target is defined from a group action, no
distribution check and no resource bound will separate the intended statistic from one
that recomputes the definition.** Such a problem can still be posed -- the intended
statistic may be genuinely unknown -- but its `problem.md` has to say that passing is
diagnostic only and acceptance requires expert review.
The mechanism belongs in `cheating/taxonomy.md`; problem `22` records it there.

Problems `14` (unicellular LLT), `15` (involution orbit harmonics), `16`
(Matchings-Jack), and `21` (threshold-graph Ehrhart) have easily counted fibers
but no known target computation that scales to the resource-probe sizes within
the checker budget. The available constructions require, respectively, an
LLT-to-Schur expansion, elimination over the function space on a matrix locus,
a Jack-basis expansion, or a q,t-Ehrhart computation.

Problems `18`, `19` and `20` (selected-area gamma-parking functions, rooted
tiered trees, and the lattice companion) sit there too: their fibers are easy to
count, but no target computation documented here scales to the probe sizes, and
the available route expands a modified Macdonald basis and changes to the
elementary basis in a degree that grows with the object.

## Adding a problem

The anti-cheat machinery is object-agnostic and reusable. A new problem type
supplies only:

- an object model and a public numerical adapter (the exact-comparison part);
- an optional `order_seed` on a statistic adapter, used to apply a secret
  single-cycle shuffle to each public fiber for referential-transparency replay;
- an adversarial probe generator that returns `(function_name, (object,))` calls
  at a requested size;
- a thin `evaluate_<kind>_submission` that runs the stages in order.

The numerical worker supplies the fresh namespaces, repeated-call wrapper, and
keyed fingerprint. `check_capability_screen`, `check_source_economy`,
`run_resource_gate` remain shared. Before relying on the checker for a new
problem, judge whether its fiber counting is hard enough for the resource gate
to be decisive.

The maintained attack catalog, including confirmed bypasses and irreducible
cases, is in `docs/cheating/taxonomy.md`.
