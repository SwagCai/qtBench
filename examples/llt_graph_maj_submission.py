# Signature template for the unicellular LLT q_statistic_discovery task
# (problem 14). A submission returns lltstat_G(T), a nonnegative integer, and the
# checker grades the objects of each Dyck graph by the shape of T.
#
# This is the natural first guess: the "G-weighted major index", which replaces
# each descent i of T by the number of left neighbours of the vertex i+1 in G,
#
#     lltstat_G(T) = sum_{i in Des(T)} #{ u < i + 1 : (u, i + 1) in E }.
#
# It matches all three anchors -- 0 on the edgeless graph, maj(T) on the complete
# graph, and the extreme values 0 and |E| on the row and column tableaux -- but it
# is not the answer: it fails the numerical stage on most Dyck graphs. It just
# shows the required shape and a reasonable place to start the search.
def statistic(graph_tableau):
    b = graph_tableau.b  # vertices u < v are adjacent iff v <= b[u - 1]
    cells = graph_tableau.cells
    total = 0
    for i in range(1, graph_tableau.n):
        if cells[i][0] > cells[i - 1][0]:  # i is a descent of T
            total += sum(1 for u in range(1, i + 1) if b[u - 1] >= i + 1)
    return total
