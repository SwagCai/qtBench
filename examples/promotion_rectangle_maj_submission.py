# Signature template for the promotion cyclic sieving q_statistic_discovery task
# (problem 22). A submission returns the exponent, and the checker grades the
# tableaux of each shape by it against the sieving polynomial C_lambda(q).
#
# This is the answer on the solved half of the problem: for a rectangle, Rhoades
# proved that promotion exhibits the cyclic sieving phenomenon with the major index,
# so the least-degree sieving polynomial is the distribution of
#
#     (maj(T) - n(lambda)) mod N,      n(lambda) = sum_i (i - 1) lambda_i,
#
# with N the number of cells. It is correct on all 19 public rectangles and wrong on
# all 3 public staircases, which is exactly the shape of the open problem: an answer
# must agree with this on rectangles and extend it to staircases, where N is twice
# the number of cells instead.
def statistic(tableau):
    return (tableau.maj() - tableau.shape_charge()) % tableau.modulus
