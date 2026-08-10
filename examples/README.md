# Example submissions

These are short, self-contained Python files in the subset admitted by the
capability screen. `noncrossing_calibration_submission.py` is a known-good
answer to the solved calibration problem and should pass every stage. The
remaining files show the **shape** of a submission rather than an answer to the
full benchmark problem and should not be expected to pass. Use them to see the
required signatures and inspect the scorer's report format.

```bash
uv run --locked python scripts/evaluate/evaluate_scored_submission.py \
  <kind> <submission.py>
```

| File | Kind | Problem | Shows |
|---|---|---|---|
| [`noncrossing_calibration_submission.py`](noncrossing_calibration_submission.py) | `noncrossing` | 1 | a complete known-good statistic that passes the scorer |
| [`constant_zero_submission.py`](constant_zero_submission.py) | `noncrossing` | 1 | the plain `statistic(object) -> int` signature |
| [`identity_bijection_submission.py`](identity_bijection_submission.py) | `area-bounce` | 2 | the `forward`/`inverse` pair of a bijection task |
| [`uig_ltr_maxima_submission.py`](uig_ltr_maxima_submission.py) | `uig` | 8 | a **composition**-valued return |
| [`kostka_maj_comaj_submission.py`](kostka_maj_comaj_submission.py) | `kostka` | 13 | a **pair** of exponents, for the problem with no public statistic |
| [`llt_graph_maj_submission.py`](llt_graph_maj_submission.py) | `llt` | 14 | a statistic on a (graph, tableau) pair |
| [`involution_moved_lds_submission.py`](involution_moved_lds_submission.py) | `involution` | 15 | a statistic on an involution, graded by its fixed-point count |
| [`mjack_within_class_submission.py`](mjack_within_class_submission.py) | `mjack` | 16 | a statistic on a (matching, partition) pair |
| [`qgamma_inv_submission.py`](qgamma_inv_submission.py) | `qgamma` | 17 | a statistic on a permutation |
| [`promotion_rectangle_maj_submission.py`](promotion_rectangle_maj_submission.py) | `promotion` | 22 | a statistic on a standard Young tableau |
| [`kreweras_area_submission.py`](kreweras_area_submission.py) | `kreweras` | 23 | a statistic graded by a type read off the object |

Each file's header comment states what its task expects. The complete list of
evaluator kinds is in [`../docs/checker.md`](../docs/checker.md); the submission
contract for a given problem is in that problem's `problem.md`.
