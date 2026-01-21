import yaml
from pathlib import Path
from collections import defaultdict


class Graph:
    def __init__(self):
        self.nodes = set()
        self.edges_out = defaultdict(list)

    def add_edge(self, src, dst, weight, lag):
        self.nodes.add(src)
        self.nodes.add(dst)
        self.edges_out[src].append({
            "to": dst,
            "weight": weight,
            "lag": lag
        })


def load_graph(path: str) -> Graph:
    graph = Graph()

    with open(path, "r") as f:
        data = yaml.safe_load(f)

    for edge in data.get("edges", []):
        graph.add_edge(
            edge["from"],
            edge["to"],
            edge.get("weight", 1.0),
            edge.get("lag_months", 0)
        )

    return graph
