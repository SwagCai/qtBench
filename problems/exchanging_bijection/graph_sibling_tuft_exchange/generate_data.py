#!/usr/bin/env python3
"""Generate public sibling/tuft data from the independent graph atlas."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from qtbench.combinatorics import ConnectedGraph, canonical_connected_graph

PROBLEM_ID = 26
PROBLEM_NAME = "graph_sibling_tuft_exchange"
EXPECTED_COUNTS = {1: 1, 2: 1, 3: 2, 4: 6, 5: 21, 6: 112, 7: 853}


def atlas_graphs(max_n: int) -> dict[int, list[ConnectedGraph]]:
    try:
        import networkx as nx
    except ImportError as error:
        raise SystemExit("generation requires the optional networkx dependency") from error
    if max_n > 7:
        raise ValueError("NetworkX's graph atlas is complete only through seven vertices")
    by_size: dict[int, list[ConnectedGraph]] = defaultdict(list)
    seen: set[str] = set()
    for graph in nx.graph_atlas_g():
        n = graph.number_of_nodes()
        if n < 1 or n > max_n or not nx.is_connected(graph):
            continue
        encoding = canonical_connected_graph(n, graph.edges())
        if encoding in seen:
            raise AssertionError(f"duplicate atlas isomorphism type: {encoding}")
        seen.add(encoding)
        by_size[n].append(ConnectedGraph(encoding, validate=False))
    for n, graphs in by_size.items():
        graphs.sort(key=lambda graph: graph.encoding)
        if len(graphs) != EXPECTED_COUNTS[n]:
            raise SystemExit(
                f"n={n}: graph atlas has {len(graphs)} connected graphs, "
                f"expected {EXPECTED_COUNTS[n]}"
            )
    return dict(by_size)


def polynomial_case(n: int, graphs: list[ConnectedGraph]) -> dict:
    distribution = Counter((graph.sibling_number(), graph.tuft_number()) for graph in graphs)
    exchanged = Counter(
        {(tuft, sibling): count for (sibling, tuft), count in distribution.items()}
    )
    if distribution != exchanged:
        raise SystemExit(f"n={n}: sibling/tuft distribution is not symmetric")
    by_reduction = defaultdict(Counter)
    for graph in graphs:
        by_reduction[graph.reduction][(graph.sibling_number(), graph.tuft_number())] += 1
    for reduction, distribution_in_fiber in by_reduction.items():
        exchanged = Counter(
            {(tuft, sibling): count for (sibling, tuft), count in distribution_in_fiber.items()}
        )
        if distribution_in_fiber != exchanged:
            raise SystemExit(
                f"n={n} reduction={reduction}: sibling/tuft distribution is not symmetric"
            )
    return {
        "case_id": f"n{n:02d}",
        "n": n,
        "count": len(graphs),
        "term_count": len(distribution),
        "reduction_fiber_count": len(by_reduction),
        "terms": [
            [sibling, tuft, distribution[(sibling, tuft)]]
            for sibling, tuft in sorted(distribution)
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--problem-dir", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--public-max-n", type=int, default=7)
    args = parser.parse_args()
    if not 1 <= args.public_max_n <= 7:
        parser.error("--public-max-n must lie between 1 and 7")
    problem_dir = args.problem_dir.resolve()
    metadata = json.loads((problem_dir / "metadata.json").read_text(encoding="utf-8"))
    if (metadata.get("id"), metadata.get("name")) != (PROBLEM_ID, PROBLEM_NAME):
        raise SystemExit(
            f"--problem-dir must identify problem {PROBLEM_ID} ({PROBLEM_NAME})"
        )
    graphs_by_size = atlas_graphs(args.public_max_n)
    cases = [polynomial_case(n, graphs_by_size[n]) for n in range(1, args.public_max_n + 1)]
    q1_cases = [
        {
            "case_id": case["case_id"],
            "n": case["n"],
            "count": case["count"],
            "term_count": len({term[1] for term in case["terms"]}),
            "terms": [
                [
                    tuft,
                    sum(
                        coefficient
                        for _sibling, other, coefficient in case["terms"]
                        if other == tuft
                    ),
                ]
                for tuft in sorted({term[1] for term in case["terms"]})
            ],
        }
        for case in cases
    ]
    identity = {"problem_id": PROBLEM_ID, "problem_name": PROBLEM_NAME}
    instance_cases = []
    for n in range(1, args.public_max_n + 1):
        entries = [
            {
                "graph": graph.encoding,
                "sibling_number": graph.sibling_number(),
                "tuft_number": graph.tuft_number(),
                "reduction": graph.reduction,
            }
            for graph in graphs_by_size[n]
        ]
        instance_cases.append(
            {"case_id": f"n{n:02d}", "n": n, "count": len(entries), "entries": entries}
        )
    data_dir = problem_dir / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    (data_dir / "polynomials.json").write_text(
        json.dumps(
            {
                "schema_version": "0.1",
                **identity,
                "variables": ["q", "t"],
                "statistics": {"q": "sibling_number", "t": "tuft_number"},
                "public_max_n": args.public_max_n,
                "case_count": len(cases),
                "cases": cases,
            },
            indent=2,
        ),
        encoding="utf-8", newline="\n",
    )
    (data_dir / "q_equals_1.json").write_text(
        json.dumps(
            {
                "schema_version": "0.1",
                **identity,
                "variables": ["t"],
                "specialization": {"q": 1},
                "meaning": "Tuft-number marginal; necessary for the exchange.",
                "public_max_n": args.public_max_n,
                "case_count": len(cases),
                "cases": q1_cases,
            },
            indent=2,
        ),
        encoding="utf-8", newline="\n",
    )
    (data_dir / "instances.json").write_text(
        json.dumps(
            {
                "schema_version": "0.1",
                **identity,
                "object_family": "unlabeled_connected_graphs",
                "statistics": ["sibling_number", "tuft_number"],
                "instances_max_n": args.public_max_n,
                "case_count": len(instance_cases),
                "cases": instance_cases,
            },
            separators=(",", ":"),
        ),
        encoding="utf-8", newline="\n",
    )

    for name in ("polynomials.json", "q_equals_1.json", "instances.json"):
        print(f"wrote {data_dir / name}")


if __name__ == "__main__":
    main()
