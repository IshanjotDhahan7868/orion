"""
Graph visualization scripts.

Use networkx or other libraries to generate visual representations of the
dependency graph for analysis and presentation.
"""

import networkx as nx
import matplotlib.pyplot as plt

def visualize_graph(graph):
    G = nx.DiGraph()
    for node in graph.nodes:
        G.add_node(node)
    for src, out_edges in graph.edges_out.items():
        for edge in out_edges:
            G.add_edge(src, edge["to"], weight=edge["weight"])

    pos = nx.spring_layout(G, seed=42)
    plt.figure(figsize=(10, 7))
    nx.draw(G, pos, with_labels=True, node_color='skyblue', edge_color='gray')
    labels = nx.get_edge_attributes(G, 'weight')
    nx.draw_networkx_edge_labels(G, pos, edge_labels=labels)
    plt.title("ORION Dependency Graph")
    plt.show()
