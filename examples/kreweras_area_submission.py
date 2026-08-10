# Signature template for the q-Kreweras q_statistic_discovery task (problem 23).
# A submission returns the exponent, and the checker groups the noncrossing
# partitions of each size by their block type and compares the resulting
# type-graded q-polynomial with Krew_lambda(q).
#
# This is the natural first guess: `area`, the statistic that already grades the
# q,t-Narayana polynomials on the very same objects in problem 1. It is right only
# for n = 1 and wrong at every other size, as is its complement
# n(n-1)/2 - area. It just shows the required shape.
#
# Two things worth knowing before searching. Summed over all block types the target
# is the MacMahon q-Catalan number (1/[n+1]_q) [2n ; n]_q, so the answer restricted
# to that coarser grading is a known q-Catalan statistic. And Krew_lambda(q) is a
# monomial times a q-multinomial, so on each type the values fill an interval-like
# pattern rather than starting at zero: the single block type (n) has the constant
# value n(n-1), and (1^n) the value 0.
def statistic(partition):
    return partition.area()
