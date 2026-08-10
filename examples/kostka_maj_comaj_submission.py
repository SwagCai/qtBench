# Signature template for the modified (q,t)-Kostka task (problem 13), the one
# problem with no public statistic. A submission returns a TUPLE of two
# nonnegative integers: the exponent of q first, the exponent of t second. Both
# are the submission's responsibility.
#
# This template returns (maj, comaj), which is right only at the two extreme mu:
# K~_{lambda (n)} = sum_T q^maj(T) forces (maj, 0), and K~_{lambda (1^n)} =
# sum_T t^maj(T) forces (0, maj), so a real answer has to interpolate between
# them as a function of mu. It just shows the required shape and the fields
# available on the object.
def statistic(tableau):
    n = tableau.n
    cells = tableau.cells  # cells[v - 1] is the 1-based (row, column) of v
    descents = [i for i in range(1, n) if cells[i][0] > cells[i - 1][0]]
    return (sum(descents), sum(n - i for i in descents))
