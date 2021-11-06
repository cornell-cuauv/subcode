import threading
import time

import shm
from mission.framework.primitive import NoOp

class Condition:
    def __init__(self, var, val, consistency=(1, 1)):
        self.var = var
        self.val = val
        self.required_failures, self.window_length = consistency
        self.results = [True] * self.window_length

    def satisfied_in_reality(self):
        if isinstance(self.var, str):
            return True
        return self.satisfied_in_state({self.var: self.var.get()})

    def assumed_value(self):
        return self.val

class EQ(Condition):
    def satisfied_in_state(self, state):
        if state[self.var] == None:
            return False
        return state[self.var] == self.val

class GE(Condition):
    def satisfied_in_state(self, state):
        if state[self.var] == None:
            return False
        return state[self.var] >= self.val

class LE(Condition):
    def satisfied_in_state(self, state):
        if state[self.var] == None:
            return False
        return state[self.var] <= self.val

class TH(Condition):
    def __init__(self, var, val, tolerance, consistency=(1, 1)):
        super().__init__(var, val, consistency)
        self.tolerance = tolerance

    def satisfied_in_state(self, state):
        if state[self.var] == None:
            return False
        return abs(state[self.var] - self.val) <= self.tolerance

class Action:
    def __init__(self, name, preconds, invariants, postconds, task, on_failure=lambda failing_var: NoOp(), dependencies=[]):
        self.name = name
        self.preconds = preconds
        self.invariants = invariants
        self.postconds = postconds
        self.task = task
        self.on_failure = on_failure
        self.dependencies = dependencies

    def state_after_action(self, all_variables):
        state = {}
        for variable in all_variables:
            state[variable] = None
        for condition in self.postconds:
            state[condition.var] = condition.assumed_value()
        return state

    def execute(self):
        while True:
            try:
                self.task()
            except Exception as e:
                print("Exception thrown by " + self.name + ": " + e)
                break
            if self.task.finished:
                break
            for condition in self.invariants:
                condition.results = condition.results[1:] + [condition.satisfied_in_reality()]
                if condition.results.count(False) >= condition.required_failures:
                    print("(Invariant) Failing variable: " + condition.var)
                    return condition.var
            time.sleep(1 / 60)
        for condition in self.postconds:
            if not condition.satisfied_in_reality():
                print("(Postcond) Failing variable: " + condition.var)
                return condition.var
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
