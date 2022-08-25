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

