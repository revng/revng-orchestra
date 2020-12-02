from concurrent import futures
from typing import List, Dict
import enlighten

from loguru import logger

from .actions.action import Action
from .util import set_terminal_title, OrchestraException


class Executor:
    def __init__(self, args, threads=1):
        self.args = args
        self.threads = 1
        self._pending_actions: List[Action] = []
        self._running_actions: Dict[futures.Future, Action] = {}
        self._failed_actions: List[Action] = []
        self._pool = futures.ThreadPoolExecutor(max_workers=threads, thread_name_prefix="Builder")

    def run(self, action, no_force=False, no_deps=False):
        self._collect_actions(action, force=not no_force, no_deps=no_deps)
        self._pending_actions.sort(key=lambda a: a.qualified_name)

        if not self._pending_actions:
            logger.info("No actions to perform")

        total_pending = len(self._pending_actions)

        for _ in range(self.threads):
            self._schedule_next()

        manager = enlighten.get_manager()
        status_bar = manager.status_bar()
        status_bar.color = "bright_white_on_lightslategray"

        while self._running_actions:
            running_jobs_str = ", ".join(a.name_for_info for a in self._running_actions.values())
            status_bar_args = {
                "jobs": running_jobs_str,
                "current": total_pending - len(self._pending_actions),
                "total": total_pending,
            }
            set_terminal_title(f"Running {running_jobs_str}")
            status_bar.status_format = "[{current}/{total}] Running {jobs}"
            status_bar.update(**status_bar_args)
            status_bar.refresh()

            done, not_done = futures.wait(self._running_actions, return_when=futures.FIRST_COMPLETED)
            for d in done:
                action = self._running_actions[d]
                del self._running_actions[d]
                exception = d.exception()
                if exception:
                    if isinstance(exception, OrchestraException):
                        logger.error(str(exception))
                        if self._pending_actions:
                            logger.error(f"Waiting for other running actions to terminate: {self._pending_actions}")
                            self._pending_actions = []
                        self._failed_actions.append(action)
                    else:
                        raise exception
                else:
                    self._schedule_next()

        if self._failed_actions:
            msg = "Failed: " + ", ".join(a.name_for_info for a in self._failed_actions)
            status_bar.color = "white_on_red"
            result = 1
        else:
            msg = "All done!"
            status_bar.color = "white_on_darkgreen"
            result = 0

        status_bar.status_format = msg
        status_bar.close()
        return result

    def _collect_actions(self, action: Action, force=False, no_deps=False):
        if not force and action.is_satisfied(recursively=True):
            return

        if action not in self._pending_actions:
            self._pending_actions.append(action)
            if no_deps:
                return

            for dep in action.dependencies:
                self._collect_actions(dep)

    def _schedule_next(self):
        next_runnable_action = self._get_next_runnable_action()
        if not next_runnable_action:
            if self._pending_actions:
                logger.error(f"Could not run any action! An action has failed or there is a circular dependency")
                self._failed_actions = list(self._pending_actions)
            return

        future = self._pool.submit(self._run_action, next_runnable_action)
        self._running_actions[future] = next_runnable_action
        return future

    def _get_next_runnable_action(self):
        for action in self._pending_actions:
            if all([d.is_satisfied(recursively=True) for d in action.dependencies]):
                self._pending_actions.remove(action)
                return action

    def _run_action(self, action: Action):
        return action.run(args=self.args)
