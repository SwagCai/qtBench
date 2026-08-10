"""Public oracle: the target polynomials E_G(q,t) of problem 21.

This public oracle is used only to
regenerate the public polynomial targets; the scored evaluator never loads it.

For a connected threshold graph ``G`` on ``{0, ..., n}`` it computes the
``(q,t)``-weighted Ehrhart function of the flow polytope with netflow
``(-n, 1, ..., 1)``, in the sense of Liu, Meszaros and Morales
(arXiv:1610.08370, Definition 2.1 and Remark 2.2):

    Ehr_{q,t}(F_G(a)) = sum_{A in F_G(a) cap Z^E} wt_{q,t}(A),
    wt_{q,t}(A) = (-(1 - t)(1 - q))^{#{a_ij > 0} - n} * prod_{i,j} wt_{q,t}(a_ij),
    wt_{q,t}(b) = (q^b - t^b)/(q - t) for b > 0, and 1 for b = 0.

Edges are oriented from ``i`` to ``j`` when ``i > j``, so an integer flow sends
out of every vertex ``i >= 1`` exactly one unit more than it receives. Theorem
3.8 there proves that ``Ehr_{q,1}(F_G)`` is the ``inv`` enumerator of the
spanning trees of ``G``; Conjecture 6.1 predicts ``Ehr_{q,t}(F_G) in N[q,t]``,
and Section 6.1 asks for the ``t``-statistic that would refine it.

Everything is exact integer arithmetic: polynomials in ``q`` and ``t`` are
dictionaries ``{(i, j): coefficient}``, and flows are streamed one at a time so
peak memory stays small.
"""
from __future__ import annotations

PROBLEM_ID = 21
PROBLEM_NAME = "tgt_inv_qt_ehrhart_second_stat"


def pmul(f, g):
    out: dict[tuple[int, int], int] = {}
    for (a, b), u in f.items():
        for (c, d), v in g.items():
            key = (a + c, b + d)
            out[key] = out.get(key, 0) + u * v
    return {key: value for key, value in out.items() if value}


def padd(f, g):
    out = dict(f)
    for key, value in g.items():
        out[key] = out.get(key, 0) + value
    return {key: value for key, value in out.items() if value}


def ppow(f, exponent):
    out = {(0, 0): 1}
    for _ in range(exponent):
        out = pmul(out, f)
    return out


def weight(b: int):
    """``wt_{q,t}(b)``, the complete homogeneous polynomial of degree ``b - 1``."""
    if b == 0:
        return {(0, 0): 1}
    return {(i, b - 1 - i): 1 for i in range(b)}


# ``-(1 - t)(1 - q)``
PREFACTOR = {(0, 0): -1, (1, 0): 1, (0, 1): 1, (1, 1): -1}


def down_neighbours(up_degrees):
    n = len(up_degrees)
    return {
        vertex: [j for j in range(vertex) if vertex <= j + up_degrees[j]]
        for vertex in range(1, n + 1)
    }


def iter_flows(up_degrees, netflow=None):
    """Stream the integer flows as ``{(i, j): value}`` dictionaries.

    Vertices are processed from ``n`` down to ``1``; each sends out its netflow
    plus everything it has received, split over its down-neighbours. The yielded
    dictionary is reused between flows, so consumers must read it before
    resuming the generator.
    """
    n = len(up_degrees)
    if netflow is None:
        netflow = [1] * n
    down = down_neighbours(up_degrees)
    flow: dict[tuple[int, int], int] = {}
    inflow = [0] * (n + 1)

    def rec(vertex):
        if vertex == 0:
            yield flow
            return
        supply = netflow[vertex - 1] + inflow[vertex]
        targets = down[vertex]
        if supply < 0 or not targets:
            return

        def walk(index, remaining):
            target = targets[index]
            if index == len(targets) - 1:
                flow[(vertex, target)] = remaining
                inflow[target] += remaining
                yield from rec(vertex - 1)
                inflow[target] -= remaining
                del flow[(vertex, target)]
                return
            for amount in range(remaining + 1):
                flow[(vertex, target)] = amount
                inflow[target] += amount
                yield from walk(index + 1, remaining - amount)
                inflow[target] -= amount
                del flow[(vertex, target)]

        yield from walk(0, supply)

    yield from rec(n)


def flow_count(up_degrees, netflow=None) -> int:
    return sum(1 for _ in iter_flows(up_degrees, netflow))


def E_poly(up_degrees, netflow=None) -> dict[tuple[int, int], int]:
    """Return ``{(i, j): coeff}`` of ``q^i t^j`` in ``Ehr_{q,t}(F_G(a))``."""
    up_degrees = tuple(int(value) for value in up_degrees)
    n = len(up_degrees)
    total: dict[tuple[int, int], int] = {}
    for flow in iter_flows(up_degrees, netflow):
        nonzero = [value for value in flow.values() if value]
        term = ppow(PREFACTOR, len(nonzero) - n)
        for value in nonzero:
            term = pmul(term, weight(value))
        total = padd(total, term)
    return total
