# Signature template for the Shareshian-Wachs q_statistic_discovery task
# (problem 8). A submission returns theta(sigma), a COMPOSITION of n (a tuple of
# positive integers summing to n); the checker uses only its underlying partition
# lambda(theta(sigma)).
#
# This is the paper's starting-point guess theta-hat: theta_hat(sigma) is the
# composition of n whose cut set is { i in [n-1] : i+1 is a left-to-right
# G-maximum of sigma }. It has the right number of parts (the number of
# left-to-right G-maxima) but only realizes chi_G for a small subclass of Dyck
# graphs, so it fails the numerical stage in general -- it just shows the
# required shape and a reasonable place to start the search.
def statistic(graph_permutation):
    perm = graph_permutation.perm
    b = graph_permutation.b  # vertices u < v are adjacent iff v <= b[u - 1]
    n = graph_permutation.n
    cuts = []
    for q in range(2, n + 1):
        value = perm[q - 1]
        is_maximum = True
        for j in range(q - 1):
            other = perm[j]
            # position q is a left-to-right G-maximum: value dominates every
            # earlier entry and is non-adjacent to it.
            if other > value or value <= b[other - 1]:
                is_maximum = False
                break
        if is_maximum:
            cuts.append(q - 1)
    points = [0] + cuts + [n]
    return tuple(points[j + 1] - points[j] for j in range(len(points) - 1))
