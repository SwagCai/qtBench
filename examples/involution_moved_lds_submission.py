# Signature template for the involution orbit-harmonics q_statistic_discovery task
# (problem 15). A submission returns istat_{n,a}(pi), a nonnegative integer, and the
# checker grades each fiber M_{n,a} = {pi : pi^2 = id, fix(pi) = a} by that exponent.
#
# This is the natural first guess: take the statistic that is known to answer the
# fixed-point-free fiber and apply it to the non-fixed letters alone,
#
#     istat(pi) = (#moved(pi) - lds(pi restricted to its non-fixed points)) / 2,
#
# with lds the length of a longest decreasing subsequence, computed below by
# patience sorting. It is always a nonnegative integer -- the restriction is a
# fixed-point-free involution, and the RSK shape of one has an even number of rows
# -- and it is exactly right on the two fibers whose answers are known: on a = 0 it
# is the Liu-Ma-Rhoades-Zhu statistic (n - lds)/2, and on a = n it is 0.
#
# It is not the answer. On the transposition fiber it returns 0 for every
# transposition, while H_{n,n-2}(q) = 1 + (C(n,2) - 1) q asks for exactly one 0. It
# just shows the required shape and a reasonable place to start the search.
def statistic(involution):
    moved = [
        value
        for index, value in enumerate(involution.images, start=1)
        if value != index
    ]
    piles = []  # the tops of the decreasing patience piles, themselves decreasing
    for value in moved:
        low = 0
        high = len(piles)
        while low < high:  # leftmost pile whose top is below value
            middle = (low + high) // 2
            if piles[middle] < value:
                high = middle
            else:
                low = middle + 1
        if low == len(piles):
            piles.append(value)
        else:
            piles[low] = value
    return (len(moved) - len(piles)) // 2
