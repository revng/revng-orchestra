import graphlib
import threading
import time
from collections import defaultdict
from concurrent import futures
from itertools import permutations, product
from typing import List, Dict

import enlighten
import networkx as nx
import networkx.classes.filters as nxfilters
from loguru import logger

from .actions import AnyOfAction, InstallAction
from .actions.action import Action, ActionForBuild
from .util import set_terminal_title, OrchestraException


class Executor:
    def __init__(self, args, actions, no_deps=False, threads=1):
        self.args = args
        self.actions = actions
        self.no_deps = no_deps
        self.threads = 1

        self._toposorter = graphlib.TopologicalSorter()
        self._pool = futures.ThreadPoolExecutor(max_workers=threads, thread_name_prefix="Builder")
        self._queued_actions: Dict[futures.Future, Action] = {}
        self._running_actions: List[Action] = []
        self._failed_actions: List[Action] = []

        self._total_remaining = None
        self._current_remaining = None
        self._stop_updating_display = False
        self._display_manager: enlighten.Manager
        self._display_thread: threading.Thread

    def run(self):
        dependency_graph = self._create_dependency_graph()

        self._verify_binary_archives_exist(dependency_graph)

        self._init_toposorter(dependency_graph)

        try:
            self._toposorter.prepare()
        except graphlib.CycleError as e:
            raise Exception(f"A cycle was found in the dependency graph: {e.args[1]}. This should never happen.")

        if not self._toposorter.is_active():
            logger.info("No actions to perform")

        self._total_remaining = dependency_graph.number_of_nodes()
        self._current_remaining = self._total_remaining

        self._start_display_update()

        # Schedule and run the actions
        while self._toposorter.is_active() and not self._failed_actions:
            for action in self._toposorter.get_ready():
                future = self._pool.submit(self._run_action, action)
                self._queued_actions[future] = action

            done, not_done = futures.wait(self._queued_actions, return_when=futures.FIRST_COMPLETED)
            for completed_future in done:
                action = self._queued_actions[completed_future]
                del self._queued_actions[completed_future]
                exception = completed_future.exception()
                if exception:
                    if isinstance(exception, OrchestraException):
                        logger.error(str(exception))
                        logger.error(f"Waiting for other running actions to terminate")
                        self._pool.shutdown(wait=True)
                        self._failed_actions.append(action)
                    else:
                        raise exception
                else:
                    self._toposorter.done(action)

        # Wait for pending actions to finish
        done, not_done = futures.wait(self._queued_actions, return_when=futures.ALL_COMPLETED)
        for completed_future in done:
            action = self._queued_actions[completed_future]
            del self._queued_actions[completed_future]
            exception = completed_future.exception()
            if exception:
                if isinstance(exception, OrchestraException):
                    logger.error(str(exception))
                    logger.error(f"Waiting for other running actions to terminate")
                    self._pool.shutdown(wait=True)
                    self._failed_actions.append(action)
                else:
                    raise exception
            else:
                self._toposorter.done(action)

        self._stop_display_update()

        return list(self._failed_actions)

    def _create_dependency_graph(self,
                                 remove_unreachable=True,
                                 simplify_anyof=True,
                                 remove_satisfied=True,
                                 intra_component_ordering=True,
                                 transitive_reduction=True,
                                 ):
        # Recursively collect all dependencies of the root action in an initial graph
        dependency_graph = self._create_initial_dependency_graph()

        # Find an assignment for all the choices so the graph becomes acyclic
        dependency_graph = self._assign_choices(dependency_graph)
        if dependency_graph is None:
            raise Exception("Could not find an acyclic assignment for the given dependency graph")

        if remove_unreachable:
            self._remove_unreachable_actions(dependency_graph, ["Dummy root"])

        if simplify_anyof:
            # The graph returned contains choices with only one alternative
            # Simplify them by turning A -> Choice -> B into A -> B
            self._simplify_anyof_actions(dependency_graph)

        # Remove the dummy root node
        true_roots = list(dependency_graph.successors("Dummy root"))
        dependency_graph.remove_node("Dummy root")
        if remove_satisfied:
            self._remove_satisfied_attracting_components(dependency_graph)
            # Re-add the true root actions as they may have been removed
            dependency_graph.add_nodes_from(true_roots)

        if intra_component_ordering:
            dependency_graph = self._enforce_intra_component_ordering(dependency_graph)

        if transitive_reduction:
            dependency_graph = self._transitive_reduction(dependency_graph)

        return dependency_graph

    def _create_initial_dependency_graph(self):
        graph = nx.DiGraph()
        for action in self.actions:
            graph.add_edge("Dummy root", action)
            self._collect_dependencies(action, graph)
        return graph

    def _collect_dependencies(self, action, graph, already_visited_nodes=None):
        if already_visited_nodes is None:
            already_visited_nodes = set()

        if action in already_visited_nodes:
            return

        already_visited_nodes.add(action)
        graph.add_node(action)
        if self.no_deps:
            return

        for dependency in action.dependencies:
            graph.add_edge(action, dependency)
            self._collect_dependencies(
                dependency,
                graph,
                already_visited_nodes=already_visited_nodes
            )

    def _assign_choices(self, graph):
        # We can assign the choices for each strongly connected component independently
        while has_choices(graph):
            strongly_connected_components = list(nx.algorithms.strongly_connected_components(graph))
            strongly_connected_components.sort(key=len, reverse=True)
            for strongly_connected_component in strongly_connected_components:
                any_of_nodes = [
                    c for c in strongly_connected_component
                    if isinstance(c, AnyOfAction) and len(list(graph.successors(c))) > 1
                ]
                if not any_of_nodes:
                    # There are no InstallAny nodes in this SCC, don't waste time
                    continue
                graph = self._assign_strongly_connected_component(graph, any_of_nodes, strongly_connected_component)
                if graph is None:
                    return graph
                break

        return graph

    def _assign_strongly_connected_component(self, graph, remaining, strongly_connected_component):
        # TODO: the copy() operation ~halves performance.
        #  The other edge/node add/removal operations have an impact as well.
        #  We can avoid them using filtered views

        # No more choices remain, check if the subgraph
        # of the stringly connected components is cyclic
        if not remaining:
            subgraph = graph.copy()
            self._remove_unreachable_actions(subgraph, ["Dummy root"])
            subgraph = subgraph.subgraph(strongly_connected_component)

            if has_unsatisfied_cycles(subgraph):
                return None
            else:
                return graph

        to_assign = remaining.pop()

        # Try all choices
        alternatives = list(graph.successors(to_assign))
        alternatives.sort(key=keyer(to_assign))

        graph.remove_edges_from((to_assign, s) for s in alternatives)

        for alternative in alternatives:
            graph.add_edge(to_assign, alternative)

            #  Assigning nodes that are not reachable from the root is pointless
            _, pointless = filter_out_unreachable(graph, remaining, ["Dummy root"])
            for n in pointless:
                remaining.remove(n)

            solved_graph = self._assign_strongly_connected_component(graph, remaining, strongly_connected_component)
            if solved_graph is None:
                graph.remove_edge(to_assign, alternative)

                for n in pointless:
                    remaining.append(n)
            else:
                return solved_graph

        graph.add_edges_from((to_assign, a) for a in alternatives)
        remaining.append(to_assign)

    @staticmethod
    def _simplify_anyof_actions(graph):
        for action in list(graph.nodes):
            if isinstance(action, AnyOfAction):
                predecessors = list(graph.predecessors(action))
                successors = list(graph.successors(action))
                assert len(successors) == 1, f"Choice {action} was not taken?"
                graph.remove_node(action)
                graph.add_edges_from((p, successors[0]) for p in predecessors)

    @staticmethod
    def _remove_unreachable_actions(graph, roots):
        # Remove all nodes that are not reachable from one of the roots
        shortest_paths = nx.multi_source_dijkstra_path_length(graph, roots)
        for node in list(graph.nodes):
            if node not in shortest_paths:
                graph.remove_node(node)

    @staticmethod
    def _remove_satisfied_attracting_components(graph):
        # Remove sets of attracting components where all components are satisfied
        fixed_point_reached = False
        done_something = False
        while not fixed_point_reached:
            fixed_point_reached = True
            for attracting_components in nx.attracting_components(graph):
                if all(c.is_satisfied() for c in attracting_components):
                    graph.remove_nodes_from(attracting_components)
                    fixed_point_reached = False
                    done_something = True
                    break
        return done_something

    def _enforce_intra_component_ordering(self, dependency_graph):
        """This pass ensures that when two builds of the same component are
        scheduled to be installed their direct antidependencies will find those exact builds
        when run.
        Example:
               +-------+
            +--+  A@1  +--+
            |  +-------+  |
        +---v---+     +---v---+
        |  B@1  |     |  A@2  +--+
        +-------+     +-------+  |
                             +---v---+
                             |  B@2  |
                             +-------+

        Wihout this pass both following schedules are both possible:
            - B@2, A@2, B@1, A@1
            - B@2, B@1, A@2, A@1
        The second schedule runs B@1 after B@2, but A@2 after B@1,
        so A@2 would not find the exact build it was expecting.

        The pass transforms the graph above into:

               +-------+
            +--+  A@1  +--+
            |  +-------+  |
        +---v---+     +---v---+
        |  B@1  +----->  A@2  +--+
        +---+---+     +-------+  |
            |                +---v---+
            +---------------->  B@2  |
                             +-------+

        For each component C the algorithm creates a list of groups of actions, one for each build.
        Each group contains:
         1. actions that pertain to a specific build of the component
         2. actions that directly depend on actions of point 1
        The algorithm tries all possible permutations of the groups in the list.
        For each permutation [G1, G2, ..., Gn] all actions in
        group Gi are marked to depend on all actions in group Gi+1.
        The graph is checked for cycles and if none are found the order is accepted.
        """
        scheduled_actions_per_build = defaultdict(set)
        scheduled_builds_per_component = defaultdict(set)
        scheduled_actions_per_direct_build_dependency = defaultdict(set)

        for action in dependency_graph.nodes:
            if isinstance(action, ActionForBuild):
                scheduled_builds_per_component[action.component].add(action.build)
                scheduled_actions_per_build[action.build].add(action)
                for d in dependency_graph.predecessors(action):
                    scheduled_actions_per_direct_build_dependency[action.build].add(d)

        groups_by_component = defaultdict(list)
        for c, blds in scheduled_builds_per_component.items():
            if len(blds) < 2:
                continue

            for bld in blds:
                group = scheduled_actions_per_build[bld].union(scheduled_actions_per_direct_build_dependency[bld])
                groups_by_component[c].append(group)

        for component, group in groups_by_component.items():
            dependency_graph = self._try_group_orders(dependency_graph, group)
            if dependency_graph is None:
                raise Exception(f"Could not enforce an order between actions of "
                                f"component {component} pertaining to multiple builds")

        return dependency_graph

    @staticmethod
    def _try_group_orders(dependency_graph, group):
        for permutation in permutations(group):
            # TODO: duplicating the graph is not good for performance,
            #  might be worth removing nodes manually
            depgraph_copy = dependency_graph.copy()

            for g1, g2 in zip(permutation, permutation[1:]):
                # Add edge from all nodes in g1 to all nodes in g2
                for a1, a2 in product(g1, g2):
                    if a1 is not a2:
                        depgraph_copy.add_edge(a1, a2)

            if not has_unsatisfied_cycles(depgraph_copy):
                return depgraph_copy

    @staticmethod
    def _transitive_reduction(graph):
        if nx.is_directed_acyclic_graph(graph):
            return nx.algorithms.dag.transitive_reduction(graph)

        # It is not possible (rather, it is expensive and not uniquely defined)
        # to compute the transitive reduction on a graph with cycles
        # So we:
        #  - perform a condensation which gives us a DAG
        #    (by "shrinking" all strongly connected components in a single node)
        #  - perform a transitive reduction
        #  - expand the condensed graph back to it's expanded form
        condensed_graph = nx.algorithms.condensation(graph)
        mapping = condensed_graph.graph["mapping"]
        members = nx.get_node_attributes(condensed_graph, "members")

        condensed_graph = nx.algorithms.transitive_reduction(condensed_graph)

        # TODO: review this code, it may be re-adding edges that
        #  were taken out by the transitive reduction
        inflated_graph = nx.DiGraph()
        for condensed_node in condensed_graph.nodes:
            condensed_node_members = members[condensed_node]
            subgraph = nx.subgraph_view(graph, filter_node=nxfilters.show_nodes(condensed_node_members))
            inflated_graph = nx.union(inflated_graph, subgraph)

            for u, v in graph.out_edges(condensed_node_members):
                v_condensed_node = mapping[v]
                if condensed_graph.has_edge(condensed_node, v_condensed_node):
                    inflated_graph.add_edge(u, v)

        return inflated_graph

    @staticmethod
    def _verify_binary_archives_exist(dependency_graph):
        for action in dependency_graph.nodes:
            if not isinstance(action, InstallAction):
                continue
            if not action.binary_archive_exists() and not action.allow_build:
                binary_archive_filename = action.build.binary_archive_filename
                qualified_name = action.build.qualified_name
                raise Exception(
                    f"""Binary archive {binary_archive_filename} for {qualified_name} not found.
                    Try `orc update` or run `orc install` with `-b`."""
                )

    def _init_toposorter(self, dependency_graph):
        for action in dependency_graph.nodes:
            dependencies = dependency_graph.successors(action)
            self._toposorter.add(action, *dependencies)

    def _run_action(self, action: Action):
        self._running_actions.append(action)
        self._current_remaining -= 1
        try:
            return action.run(args=self.args)
        finally:
            self._running_actions.remove(action)

    def _start_display_update(self):
        self._stop_updating_display = False
        # Display manager and status bar must be initialized in main thread
        self._display_manager = enlighten.get_manager()
        self._status_bar = self._display_manager.status_bar()
        self._display_thread = threading.Thread(target=self._update_display, name="Display updater")
        self._display_thread.start()

    def _stop_display_update(self):
        self._stop_updating_display = True

    def _update_display(self):
        self._status_bar.color = "bright_white_on_lightslategray"
        try:
            while not self._stop_updating_display:
                running_jobs_str = ", ".join(a.name_for_info for a in self._running_actions)
                self._status_bar_args = {
                    "jobs": running_jobs_str,
                    "current": self._total_remaining - self._current_remaining,
                    "total": self._total_remaining,
                }
                set_terminal_title(f"Running {running_jobs_str}")
                self._status_bar.status_format = "[{current}/{total}] Running {jobs}"
                self._status_bar.update(**self._status_bar_args)
                self._status_bar.refresh()
                time.sleep(0.3)
        finally:
            self._status_bar.close()


def has_unsatisfied_cycles(graph):
    simple_cycles = list(nx.simple_cycles(graph))
    for cycle in simple_cycles:
        if not all(c.is_satisfied() for c in cycle):
            return True
    return False


def has_choices(graph):
    for node in graph.nodes:
        if isinstance(node, AnyOfAction) and len(list(graph.successors(node))) > 1:
            return True
    return False


def keyer(to_assign):
    def _keyer(action):
        """
        Prioritize choices in this order:
         - installed build
         - preferred build (either explicitly specified or default)
         - all others in alphabetical order
        """
        if action.is_satisfied():
            priority = 0
        elif action is to_assign.preferred_action:
            priority = 1
        else:
            priority = 2
        return priority, str(action)

    return _keyer


def filter_out_unreachable(graph, nodes, roots):
    shortest_paths = nx.multi_source_dijkstra_path_length(graph, roots)
    reachable = []
    unreachable = []
    for node in nodes:
        if node not in shortest_paths:
            unreachable.append(node)
        else:
            reachable.append(node)
    return reachable, unreachable
