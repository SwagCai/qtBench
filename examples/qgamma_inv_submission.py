# Signature template for the q-Eulerian gamma q_statistic_discovery task
# (problem 17). A submission returns qgamma(sigma), a nonnegative integer, and the
# checker grades each fiber Gamma_{n,k} -- permutations with k-1 descents, none of
# them double or final -- by that exponent.
#
# This is the natural first guess: the inversion number,
#
#     qgamma(sigma) = #{ i < j : sigma(i) > sigma(j) },
#
# the Mahonian statistic that already grades the q-Eulerian polynomial itself. It is
# right on the singleton fibers k = 1 and on Gamma_{3,2}, where the two objects 213
# and 312 have inv 1 and 2 and a_{3,2}(q) = q + q^2. It is not the answer: it fails
# on every other fiber, and the plain major index does no better.
#
# Note the shape as much as the content: the resource probes reach n = 1024, so a
# submission should stay near-linear. The object counts inversions in O(n log n) --
# writing the quadratic double loop here instead is enough to blow the probe budget.
def statistic(permutation):
    return permutation.inv()
