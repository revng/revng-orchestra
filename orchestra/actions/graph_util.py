import networkx as nx

from .any_of import AnyOfAction
from .action import Action


def assign_style(graph):
    """Applies style attributes to the nodes of a dependency graph.

    The node shape is set to "box" and the following colors are applied depending on the node type:

    - AnyOf: lightblue
    - Satisfied actions: green
    - Unsatisfied actions: white
    """
    styles = {}
    for node in graph.nodes:
        if isinstance(node, AnyOfAction):
            color = "lightblue"
        elif isinstance(node, Action) and node.is_satisfied():
            color = "green"
        else:
            color = "white"
        styles[node] = {
            "shape": "box",
            "style": "filled",
            "fillcolor": color,
        }
    nx.set_node_attributes(graph, styles)


def show_graph(graph):
    """
    Debugging utility to dump a graph
    """
    assign_style(graph)
    fname = "/tmp/graph.svg"
    nx.nx_agraph.view_pygraphviz(graph, path=fname, show=False, args="-Gsplines=ortho")
