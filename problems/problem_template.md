# Problem Title

## Task

State the discovery target in one paragraph. The task type is the directory the
problem lives in, one of:

- `t_statistic_discovery`
- `q_statistic_discovery`
- `exchanging_bijection`

Say how many statistics are public and what the submission has to supply; that
is data (`known_statistic`, or `known_statistics` of length 0, 2, ...), not a
separate task type.

## Objects

Define the combinatorial objects and the canonical JSON/Python encoding.

## Public Statistic(s)

Describe every public statistic and its implementation. A problem with no
public statistic states that explicitly and omits the known-statistic file.

## Public Data

List the public ranges and the files exposed to participants. For q,t tasks,
include `data/q_equals_1.json`, the specialization of the leading grading
variable to `1`, which gives a necessary one-variable distribution for the
unknown statistic. The filename is conventional: for a problem graded by
`u = q - 1` it records `u = 1`, and the statement must say so.

## Submission

Specify the exact Python function signature. Statistic tasks define
`statistic`; bijection tasks define both `forward` and `inverse`. Identify
the problem-specific checker adapter and resource probe size.

```python
def statistic(obj) -> int:
    ...
```

## Scoring

Describe the capability and source-economy screens, public target cases, exact
comparison, fresh-namespace shuffled replay, and resource gate. State that
passing is a necessary, not a sufficient, condition (see
`docs/checker.md`).

## References

List the public papers that define the target polynomials, object family, and
problem. Public generation and certification scripts can also be noted here,
but no generator or oracle may be loaded by the scored evaluator.
