import threading
import time

import shm
from mission.framework.primitive import NoOp

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

class State:
    def __init__(self, shm_values={}, flags=set()):
        self.shm_values = shm_values.copy()
        self.flags = flags.copy()

    def satisfies_conditions(self, conditions):
        for condition in conditions:
            if isinstance(condition, Condition):
                if not condition.satisfied_in_state(self):
                    return False
            else:
                if condition not in self.flags:
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

class Condition:
    def __init__(self, var, val, consistency=(1, 1)):
        self.var = var
        self.val = val
        self.required_failures, self.window_length = consistency
        self.results = [True] * self.window_length

    def satisfied_in_reality(self):
        return self.satisfied_in_state(State(shm_values={self.var: self.var.get()}))

    def assumed_values(self):
        return {self.var: self.val}

    def update_result(self):
        self.results = self.results[1:] + [self.satisfied_in_reality()]

    def failing_cond(self):
        return self

class EQ(Condition):
    def satisfied_in_state(self, state):
        if self.var not in state.shm_values:
            return False
        return state.shm_values[self.var] == self.val

class GE(Condition):
    def satisfied_in_state(self, state):
        if self.var not in state.shm_values:
            return False
        return state.shm_values[self.var] >= self.val

class LE(Condition):
    def satisfied_in_state(self, state):
        if self.var not in state.shm_values:
            return False
        return state.shm_values[self.var] <= self.val

class TH(Condition):
    def __init__(self, var, val, tolerance, consistency=(1, 1)):
        super().__init__(var, val, consistency)
        self.tolerance = tolerance

    def satisfied_in_state(self, state):
        if self.var not in state.shm_values:
            return False
        return abs(state.shm_values[self.var] - self.val) <= self.tolerance

class ALL(Condition):
    def __init__(self, conditions, consistency=(1, 1)):
        self.conditions = conditions
        self.required_failures, self.window_length = consistency
        self.results = [True] * self.window_length

    def satisfied_in_reality(self):
        return all([condition.satisfied_in_reality() for condition in self.conditions])

    def assumed_values(self):
        values = {}
        for condition in self.conditions:
            values.update(condition.assumed_values())
        return values

    def satisfied_in_state(self, state):
        return all([condition.satisfied_in_state(state) for condition in self.conditions])

    def update_result(self):
        for condition in self.conditions:
            condition.update_result()
        results = results[1:] + [self.satisfied_in_reality()]

    def failing_cond(self):
        for condition in self.conditions:
            if condition.results.count(False) >= condition.required_failures():
                return condition
        return self

class Action:
    def __init__(self, name, preconds, invariants, postconds, task, on_failure=lambda failing_var: NoOp(), time=None, dependencies=[]):
        self.name = name
        self.preconds = preconds
        self.invariants = invariants
        self.postconds = postconds
        self.task = task
        self.on_failure = on_failure
        self.time = time
        self.dependencies = dependencies
        self.currently_executing = False

    def state_after_action(self, state_before_action):
        state = State(flags=state_before_action.flags)
        state.clear_ephemeral_flags()
        for condition in self.postconds:
            if isinstance(condition, Condition):
                state.shm_values.update(condition.assumed_values())
            else:
                state.flags.add(condition)
        return state

    def execute(self):
        self.currently_executing = True
        for condition in self.invariants:
            watcher = shm.watchers.watcher()
            watcher.watch(getattr(shm, str(condition.var).split('.')[1]))
            threading.Thread(target=self.consistency_thread, args=[condition, watcher], daemon=True).start()
        while True:
            try:
                self.task()
            except Exception as e:
                print("Exception thrown by " + self.name + ": " + e)
                break
            if self.task.finished:
                break
            for condition in self.invariants:
                if condition.results.count(False) >= condition.required_failures:
                    print("(Invariant) Failing condition: " + str(condition.failing_cond())[8:-2])
                    return condition.failing_cond()
            time.sleep(1 / 60)
        self.currently_executing = False
        for condition in self.postconds:
            if isinstance(condition, Condition):
                if not condition.satisfied_in_reality():
                    print("(Postcond) Failing condition: " + str(condition.failing_cond())[8:-2])
                    return condition.failing_cond()
        return None

    def run_on_failure(self, failing_var):
        cleanup_task = self.on_failure(failing_var)
        while True:
            try:
                cleanup_task()
            except:
                return
            if cleanup_task.finished:
                return
            time.sleep(1 / 60)

    def dependencies_functioning(self):
        for dependency in self.dependencies:
            if not dependency.get():
                return False
        return True

    def consistency_thread(self, condition, watcher):
        while self.currently_executing:
            condition.update_result()
            watcher.wait()
