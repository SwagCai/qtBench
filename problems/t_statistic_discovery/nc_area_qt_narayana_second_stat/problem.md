# Noncrossing q,t-Narayana Area Partner

## Task

Find a statistic `statistic(pi)` on noncrossing partitions such that the joint distribution

```text
sum_pi q^area(pi) t^statistic(pi)
```

matches the target q,t-Narayana polynomial for every tested `NC(n,k)` fiber.

This `t_statistic_discovery` task publishes one statistic, `area`, and asks for
its t-partner.

**This solved problem is the benchmark's calibration case.** Unlike the other
twenty-nine, it has a known answer, which ships in this repository: the
adjacent `oracle.py` implements a statistic that reproduces every public target,
and the same code is the known-good fixture the checker's own test suite uses to
confirm that a genuine statistic is admitted. It remains public to demonstrate
that the evaluator accepts a true answer as well as rejecting wrong ones. Treat
a pass on problem `1` as a check that a pipeline works, never
as a discovery. Anyone using qtBench to measure discovery should exclude it or
report it separately.

## Objects

`NC(n,k)` is the Type A set of noncrossing partitions of `[n] = {1,...,n}` with `n - k + 1` blocks. A partition is encoded as a sorted list of sorted blocks:

```json
[[1,4],[2,3],[5]]
```

The Python submission receives a `NoncrossingPartition` object with:

- `partition.n`
- `partition.blocks`
- `partition.blocks_by_max`
- `partition.block_maxima`
- `partition.block_sizes_by_max`
- `partition.nonmaximal_elements`
- `partition.area()`

## Public Statistic

Order the blocks by increasing maximum:

```text
B_1, ..., B_h
```

Let `M_i = max(B_i)` and let `S_i` be the total size of the blocks before `B_i` in this order. The public statistic is

```text
area(pi) = sum_i (M_i - S_i) - n.
```

The same algorithm is implemented in `known_statistic.py`.

## Public Data

`data/polynomials.json` contains the target q,t-polynomial terms for every `NC(n,k)` with `1 <= n <= 10` and `1 <= k <= n`.

`data/q_equals_1.json` contains the specialization obtained by setting `q = 1` in each public q,t-polynomial. This is the required one-variable distribution of the unknown t-statistic, so matching it is a necessary condition for a proposed statistic, but it is not sufficient to solve the full q,t task.

`data/instances.json` contains the corresponding public objects and their `area` values. It does not contain the target t-statistic.

## Submission

Submit a restricted Python file defining:

```python
def statistic(partition) -> int:
    ...
```

The return value must be a nonnegative integer. The submission must be short,
self-contained Python; see `docs/checker.md` for the admission checks.

To score it:

```bash
uv run --frozen python scripts/evaluate/evaluate_scored_submission.py noncrossing path/to/submission.py
```

## Scoring

After the capability and source-economy screens, the evaluator enumerates each
public `NC(n,k)` fiber once. From the same submitted values, it checks every
explicit marginal in `data/q_equals_1.json` and every coefficient in
`data/polynomials.json`. Only a complete numerical match proceeds to
fresh-namespace shuffled replay and large adversarial
noncrossing partitions under CPU and memory limits. A mismatch stops the
evaluation, and passing q=1 alone is insufficient. Every stage must pass, though
a pass is necessary but not sufficient for a genuine statistic (see
`docs/checker.md`).

## References
- Jean-Christophe Aval, Michele D'Adderio, Mark Dukes, Angela Hicks, and Yvan Le Borgne, "Statistics on parallelogram polyominoes and a q,t-analogue of the Narayana numbers", arXiv:1301.4803, https://arxiv.org/abs/1301.4803.
- Eugenio Cainelli, Lorenzo Luccioli, Alessandro Iraci, Michele D'Adderio, and Giovanni Paolini, "Mapping Uncharted Symmetries: Machine Discovery in Combinatorics", arXiv:2605.19063, https://arxiv.org/abs/2605.19063.
