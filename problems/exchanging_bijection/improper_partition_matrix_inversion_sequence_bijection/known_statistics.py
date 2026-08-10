"""Public grading for problem 30."""

PROBLEM_ID = 30
PROBLEM_NAME = "improper_partition_matrix_inversion_sequence_bijection"


def semi_weight(obj) -> int:
    if obj.side != "source":
        raise ValueError("semi-weight is defined on partition matrices")
    return obj.grading


def distinct_entries(obj) -> int:
    if obj.side != "target":
        raise ValueError("distinct-entry grading is defined on inversion sequences")
    return obj.grading


def grading(obj) -> int:
    return obj.grading
