# Cheating analysis

This directory records mechanical failure modes in statistic- and
bijection-discovery checks. Its practical purpose is to keep the threat model
explicit, preserve confirmed counterexamples, and trace checker changes back to
documented attacks.

Start with the [taxonomy](taxonomy.md). Each entry has a stable identifier, the
mechanism, the checker property it attacks, the current mitigation, and the
residual limitation. A new attack should extend an existing entry when the
mechanism is the same; add a new identifier only for a genuinely different
mechanism.

The taxonomy does not define mathematical meaningfulness. A pure,
deterministic, polynomial-time rank assignment can satisfy every observable
target identity while remaining combinatorially uninformative. Mechanical
checks can reject important classes of shortcuts, but passing remains necessary
rather than sufficient evidence of a genuine discovery.

The optional model-assisted review uses the versioned instruction in
[`ai_judge_prompt.md`](ai_judge_prompt.md). It is an advisory layer only; see
the [README](../../README.md#ai-judge) for setup and limits,
or [`../ai_judge.md`](../ai_judge.md) for the technical adapter protocol.
