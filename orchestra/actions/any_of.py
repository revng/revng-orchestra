from typing import Set, Union

from .action import Action


class AnyOfAction:
    # Used to assign a unique number so that when printing a graph
    # the node does not get aliased
    INSTANCE_COUNTER = 1

    def __init__(self, actions: Set[Union[Action, "AnyOfAction"]], preferred_action: Action):
        self.actions: Set[Union[Action, "AnyOfAction"]] = actions
        self.preferred_action: Union[Action, "AnyOfAction"] = preferred_action
        self.unique_number = AnyOfAction.INSTANCE_COUNTER
        AnyOfAction.INSTANCE_COUNTER += 1

    def add_explicit_dependency(self, dependency: Union[Action, "AnyOfAction"]):
        for action in self.actions:
            action.add_explicit_dependency(dependency)

    @property
    def dependencies(self) -> Set[Union[Action, "AnyOfAction"]]:
        return {a for a in self.actions}

    @property
    def dependencies_for_hash(self) -> Set[Union[Action, "AnyOfAction"]]:
        return self.dependencies

    def is_satisfied(self):
        return any(d.is_satisfied() for d in self.dependencies)

    @property
    def name_for_components(self):
        return f"Any of {{{', '.join(a.name_for_components for a in self.actions)}}}"

    def __str__(self):
        return f"AnyOf [{self.unique_number}]"

    def __repr__(self):
        return f"Any of {{{', '.join(a.name_for_components for a in self.actions)}}}"

    def __eq__(self, other):
        if not isinstance(other, AnyOfAction):
            return False

        return self.dependencies == other.dependencies and self.preferred_action == other.preferred_action

    def __hash__(self):
        # TODO: implement properly
        return 0
