# Reporting benchmark results

qtBench issues a problem-level admission result. It does not define a single
aggregate benchmark score. Report the per-problem results so that a reader can
separate mechanical admission from evidence of mathematical discovery.

For each evaluated submission, retain the JSON output from
`evaluate_scored_submission.py --format json` and report:

- the problem ID, name, and evaluator kind;
- the checker version, complete `scoring_config`, and generated `run_seed`;
- `automatic_verdict` and `expert_review_required`, preserving `null` as “no
  automatic verdict” rather than coercing it to a failure;
- the repository commit and dirty-tree flag;
- the target-bundle and submission SHA-256 values;
- the terminal checker stage and per-case result; and
- the model and harness, prompt and tool policy, attempt budget, retries, human
  intervention, and wall-clock budget used to produce the submission.

The receipt is informational rather than a signature. An external evaluation
should run the checker in its own trusted environment instead of accepting a
submitter-produced JSON result as proof.

Output from the unrestricted `evaluate_submission.py` diagnostic is not an
admission result or receipt and must not be reported as one. The diagnostic
imports its input with the caller's privileges, so an untrusted submission can
also alter or forge that output; run such input only in an external
operating-system sandbox.

Keep these cases separate in any summary:

- Problem `1` is a solved calibration. Report it as a pipeline check and exclude
  it from discovery rates.
- Problem `22` has no automatic admission verdict. Report the deterministic
  checker output, if used diagnostically, separately from the required expert
  source review.
- A pass on problem `3` establishes agreement with the committed conditional
  targets; it does not independently derive or certify those targets.

Passing every mechanical gate is necessary, not sufficient, for a genuine
mathematical result. Any aggregate derived by a downstream evaluation must state
its denominator and treatment of expert-review, conditional-target, failed, and
unevaluated problems, and should accompany the per-problem table rather than
replace it.
