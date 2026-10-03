# Problem bank plan

The benchmark currently registers 30 problems and is intended to grow to roughly
50. The registered distribution is 13 `t_statistic_discovery`, 8
`q_statistic_discovery`, and 9 `exchanging_bijection`. The catalogue with
stable IDs and links is in
[`problems.md`](../problems.md); the machine-readable list is
[`problems/registry.json`](../problems/registry.json).

The long-term bank should retain meaningful coverage of all three task types:

- second-statistic discovery tasks from q,t-Catalan, q,t-Narayana,
  Fuss/rational variants, and related noncrossing families;
- q-statistic discovery tasks from one-variable specializations and
  q-analogues; and
- bijection tasks that explain equidistributions, symmetries, and
  weight-preserving identities.

The approximate total is a planning target, not a fixed per-type quota.

A task type is added only when a problem needs one. The existing types cover
every registered problem. A distinction that can be represented as a field --
the number of public statistics, for example -- remains a field.

## Criteria for adding a problem

- The target is a recognized open question or an established q,t-identity, cited
  in the problem statement.
- The complete scored range is published, and its reproduction path is public
  and documented in [`data_generation.md`](data_generation.md). Most generators
  live beside their problem; problems `4` and `5` share a generator, and any
  committed-target re-emission exception such as problem `3` is stated explicitly.
- The problem is mathematically distinct from every registered problem: its
  object fibers or its required identity must differ, not only its presentation.
- Its fiber counting and target recomputation costs are assessed against the
  checker's limits, and any irreducible bypass is stated in the problem
  statement and in [`cheating/taxonomy.md`](cheating/taxonomy.md). Passing the
  checker is a necessary, not a sufficient, condition (see
  [`checker.md`](checker.md)).

The authoring procedure is in [`problem_authoring.md`](problem_authoring.md).
