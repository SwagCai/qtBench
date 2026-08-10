# Provenance boundary

This directory contains the committed records consumed by `generate_data.py`:

- `type_b_qt_catalan_known_n1_to_n6.json` contains completed targets. Its
  `n = 1` value is attributed to the cyclic `B_1 = C_2` formula, its
  `n = 2,3,4` values to Stump's Appendix A table, and its `n = 5,6` values to
  reported direct diagonal-coinvariant computations.
- `type_b_qt_catalan_sl2_pattern_n7_n8.json` and
  `type_b_qt_catalan_sl2_pattern_n9.json` contain the selected conditional
  SL2-string completions and summaries of the assumptions used.
- `type_b_qt_catalan_n*_known_partial.json` contains aggregate reported
  partial-coefficient records used during those reconstructions.

These files support exact re-emission of the benchmark targets and inspection
of the recorded assumptions. They do not provide an independently reproducible
derivation. In particular, the direct-rank implementation and raw computation
records for `n = 5,6`, the reconstruction program and raw solver records for
`n = 7,8,9`, and the `work/` files named by `source_file` fields are not included
in this repository. Consequently, `generate_data.py` verifies totals,
q,t-symmetry, and the area marginal of the committed polynomials but does not
establish the reported direct computations, uniqueness, or objective-invariance
claims.
