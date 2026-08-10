# Generation notes

`generate_data.py` independently enumerates both sides of Chern--Fu Question
5.5 for `3 <= n <= 9`. All `n!` partition matrices are generated through the
standard Claesson--Dukes--Kubitzke correspondence with unrestricted inversion
sequences and then filtered by the published improper and minus conditions.
The target is separately filtered for the no-nonadjacent-repeat and minus
conditions. The generator asserts equality of every grading distribution.

The seven fibers contain 4,983 scored source objects. Generation is exhaustive,
deterministic, and uses no private oracle.
