# Signature template for the Matchings-Jack q_statistic_discovery task (problem 16).
# A submission returns mjack(delta), a nonnegative integer, and the checker grades
# the objects of each partition lambda by the pair of cycle types
# (pi, sigma) = (Lambda(delta, eps), Lambda(delta, delta_lambda)).
#
# This is the natural first guess: count the pairs of delta that stay inside one
# class of N_n = {1..n} u {1h..nh},
#
#     mjack(delta) = #{ {i, j} in delta : i, j both unhatted or both hatted } / 2,
#
# which is a nonnegative integer because each class contributes the same number of
# within-class pairs. It meets the one anchor the conjecture states outright -- it
# vanishes exactly on the bipartite matchings, so it gets the constant term
# c^lambda_{pi,sigma}(0) right whenever that term is the whole polynomial -- but it
# is not the answer: it ignores lambda entirely, while the target does not. It just
# shows the required shape and a reasonable place to start the search.
def statistic(jack_matching):
    n = jack_matching.n
    within = 0
    for i, j in jack_matching.pairs:
        if (i <= n) == (j <= n):
            within += 1
    return within // 2
