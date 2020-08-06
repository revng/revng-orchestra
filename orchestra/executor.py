import logging
from concurrent import futures

from .model.actions.action import Action


class Executor:
    def __init__(self, threads=1, show_output=False):
        self.pending_actions = set()
        self.futures = []
        self.threads = 1
        self.show_output = show_output
        self.pool = futures.ThreadPoolExecutor(max_workers=threads, thread_name_prefix="Builder")

    def run(self, action, force=False):
        self._collect_actions(action, force=force)

        for _ in range(self.threads):
            self._schedule_next()

        while self.futures:
            done, not_done = futures.wait(self.futures, return_when=futures.FIRST_COMPLETED)
            for d in done:
                self.futures.remove(d)
                self._schedule_next()

        if self.pending_actions:
            logging.error("Could not schedule any action, something failed")
            logging.error(f"Remaining: {self.pending_actions}")
            breakpoint()

    def _collect_actions(self, action: Action, force=False):
        if not force and action.is_satisfied():
            return

        if action not in self.pending_actions:
            self.pending_actions.add(action)
            for dep in action.dependencies:
                self._collect_actions(dep)

    def _schedule_next(self):
        next_runnable_action = self._get_next_runnable_action()
        if not next_runnable_action:
            logging.debug(f"Did not find more runnable actions")
            return

        future = self.pool.submit(self._run_action, next_runnable_action)
        self.futures.append(future)

    def _get_next_runnable_action(self):
        for action in self.pending_actions:
            if all([d.is_satisfied() for d in action.dependencies]):
                self.pending_actions.remove(action)
                return action

    def _run_action(self, action: Action):
        action.run(show_output=self.show_output)
