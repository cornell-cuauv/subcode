import threading
import time
import copy

import shm
from mission.framework.primitive import NoOp

class State:
    def __init__(self, shm_values={}, flags=set()):
        self.shm_values = shm_values.copy()
        self.flags = flags.copy()

    # If every comparison is satisfied by known shm values and every flag is
    # present.
    def satisfies_conditions(self, conditions):
        for condition in conditions:
            if isinstance(condition, Comparison):
                if not condition.satisfied_in_state(self):
                    return False
            elif condition not in self.flags:
                return False
        return True

    def clear_ephemeral_flags(self):
        self.flags = {flag for flag in self.flags if not flag.ephemeral}

    def __str__(self):
        shm_values_str = ", ".join(sorted([str(var)[8:-2] + ": " + str(val) for var, val in self.shm_values.items()]))
        flags_str = ", ".join(sorted(map(str, self.flags)))
        if shm_values_str and flags_str:
            return shm_values_str + ", " + flags_str
        return shm_values_str + flags_str

    def __eq__(self, other):
        return isinstance(other, State) and str(self) == str(other)

    def __hash__(self):
        return hash(str(self))

# A flag which can be present or not in state, intended to represent an event
# having occured, an option being available, etc.
class Flag:
    def __init__(self, name, ephemeral=False):
        self.name = name
        self.ephemeral = ephemeral

    def __str__(self):
        return self.name

    def __eq__(self, other):
        return str(self) == str(other)

    def __hash__(self):
        return hash(str(self))

# A condition based on a shm variable which can be verified, usually a
# relation between a shm variable and expected value.
class Comparison:
    def __init__(self, var, val, consistency=(1, 1)):
        self.var = var
        self.val = val
        self.required_failures, self.window_length = consistency
        self.results = [True] * self.window_length

    def satisfied_in_reality(self):
        reality = State(shm_values={self.var: self.var.get()})
        return self.satisfied_in_state(reality)

    def update_result(self):
        self.results = self.results[1:] + [self.satisfied_in_reality()]

class EQ(Comparison):
    def satisfied_in_state(self, state):
        if self.var not in state.shm_values:
            return False
        return state.shm_values[self.var] == self.val

class GE(Comparison):
    def satisfied_in_state(self, state):
        if self.var not in state.shm_values:
            return False
        return state.shm_values[self.var] >= self.val

class LE(Comparison):
    def satisfied_in_state(self, state):
        if self.var not in state.shm_values:
            return False
        return state.shm_values[self.var] <= self.val

class TH(Comparison):
    def __init__(self, var, val, tolerance, consistency=(1, 1)):
        super().__init__(var, val, consistency)
        self.tolerance = tolerance

    def satisfied_in_state(self, state):
        if self.var not in state.shm_values:
            return False
        return abs(state.shm_values[self.var] - self.val) <= self.tolerance

class Action:
    def __init__(self, name, preconds, invariants, postconds, task, on_failure=lambda failing_comparison: NoOp(), time=None, dependencies=[]):
        self.name = name
        self.preconds = preconds
        self.invariants = invariants
        self.postconds = postconds
        self.task = task
        self.on_failure = on_failure
        self.time = time
        self.dependencies = dependencies
        self.currently_executing = False

    # What the planner can assume will be true after this action is executed.
    def state_after_action(self, state_before_action):
        state = State(flags=state_before_action.flags)
        state.clear_ephemeral_flags()
        for condition in self.postconds:
            if isinstance(condition, Comparison):
                state.shm_values[condition.var] = condition.val
            else:
                state.flags.add(condition)
        return state

    # Run the task, checking comparisons as nessecary.
    # If a comparison fails, return it.
    def execute(self):
        self.currently_executing = True
        
        # Monitor shm variables associated with invariants on parallel threads,
        # to keep up to date with when they fail.
        for comparison in self.invariants:
            watcher = shm.watchers.watcher()
            watcher.watch(getattr(shm, str(comparison.var).split('.')[1]))
            threading.Thread(target=self.consistency_thread,
                             args=[comparison, watcher],
                             daemon=True).start()
        
        # Run the task's run() method every 60th of a second, checking that
        # all invariants are maintained.
        task_copy = copy.deepcopy(self.task)
        while True:
            try:
                task_copy()
            except Exception as e:
                print("Exception thrown by " + self.name + ": " + e)
                break
            if task_copy.finished:
                break
            for comparison in self.invariants:
                if comparison.results.count(False) >= comparison.required_failures:
                    print("(Invariant) Failing variable: " + str(comparison.var)[12:-2])
                    return comparison
            time.sleep(1 / 60)

        self.currently_executing = False
        
        # Check that all postconditions hold.
        for condition in self.postconds:
            if isinstance(condition, Comparison):
                if not condition.satisfied_in_reality():
                    print("(Postcond) Failing variable: " + str(condition.var)[12:-2])
                    return condition
        return None

    # Reset the sub in some way after a failure, by running the task given by
    # self.on_failure() parameterized on the comparison which failed.
    def run_on_failure(self, failing_comparison):
        cleanup_task = self.on_failure(failing_comparison)
        while True:
            try:
                cleanup_task()
            except Exception as e:
                print("Exception thrown during cleanup: " + e)
                return
            if cleanup_task.finished:
                return
            time.sleep(1 / 60)

    # Check all the shm variables listed as dependencies for this action.
    def dependencies_functioning(self):
        for dependency in self.dependencies:
            if not dependency.get():
                return False
        return True

    # Monitor shm variables in the background while the task runs.
    def consistency_thread(self, comparison, watcher):
        while self.currently_executing:
            comparison.update_result()
            watcher.wait()
