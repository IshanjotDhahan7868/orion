"""
Dependency graph loader and traversal logic.

Supports ORION graph schema with list-based nodes using `id`.
"""

import yaml
from collections import defaultdict


class DependencyGraph:
    def __init__(self):
        self.nodes = set()
        self.edges_out = defaultdict(list)
        self.node_meta = {}

    @classmethod
    def from_yaml(cls, path):
        with open(path, "r") as f:
            data = yaml.safe_load(f)

        graph = cls()

        # ---- LOAD NODES (id-based, ORION schema) ----
        for node in data.get("nodes", []):
            if not isinstance(node, dict) or "id" not in node:
                raise ValueError(f"Invalid node format: {node}")

            node_id = node["id"]
            graph.nodes.add(node_id)
            graph.node_meta[node_id] = node

        # ---- LOAD EDGES ----
        for edge in data.get("edges", []):
            graph.edges_out[edge["from"]].append({
                "to": edge["to"],
                "weight": edge.get("weight", 1.0),
                "lag_months": edge.get("lag_months", 0)
            })

        return graph

    def out_edges(self, node_id):
        return self.edges_out.get(node_id, [])

    def __contains__(self, node_id):
        return node_id in self.nodes
