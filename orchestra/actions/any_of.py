class AnyOfAction:
    # Used to assign a unique number so that when printing a graph
    # the node does not get aliased
    INSTANCE_COUNTER = 1

    def __init__(self, actions, preferred_action):
        self.actions = actions
        self.preferred_action = preferred_action
        self.unique_number = AnyOfAction.INSTANCE_COUNTER
        AnyOfAction.INSTANCE_COUNTER += 1

    def add_explicit_dependency(self, dependency):
        for action in self.actions:
            action.add_explicit_dependency(dependency)

    @property
    def dependencies(self):
        return {a for a in self.actions}

    def is_satisfied(self):
        return any(d.is_satisfied() for d in self.dependencies)

    @property
    def name_for_components(self):
        return f"Any of {{{', '.join(a.name_for_components for a in self.actions)}}}"

    def __str__(self):
        return f"AnyOf [{self.unique_number}]"

    def __repr__(self):
        return f"AnyOf [{self.unique_number}]"
