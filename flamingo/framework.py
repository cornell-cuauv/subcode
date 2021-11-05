import threading
import time

import shm
from mission.framework.primitive import NoOp

class Condition:
    def __init__(self, variable, test, consistency=(1, 1)):
        self.variable = variable
        self.test = test
        self.required_failures, self.window_length = consistency
        self.results = [True] * self.window_length

    def satisfied_in_reality(self):
        if not "." in self.variable:
            return True
        group, _, name = self.variable.partition(".")
        real_value = getattr(getattr(shm, group), name).get()
        return self.test.satisfied_in_state(self.variable, {self.variable: real_value})

class Test:
    def __init__(self, val):
        self.val = val

    def assumed_value(self):
        return self.val
    
    def satisfied_in_state(self, state):
        return False

class EQ(Test):
    def satisfied_in_state(self, variable, state):
        if state[variable] == None:
            return False
        return state[variable] == self.val

class GE(Test):
    def satisfied_in_state(self, variable, state):
        if state[variable] == None:
            return False
        return state[variable] >= self.val

class LE(Test):
    def satisfied_in_state(self, variable, state):
        if state[variable] == None:
            return False
        return state[variable] <= self.val

class TH(Test):
    def __init__(self, val, tolerance):
        self.val = val
        self.tolerance = tolerance

    def satisfied_in_state(self, variable, state):
        if state[variable] == None:
            return False
        return abs(state[variable] - self.val) <= self.tolerance

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
            state[condition.variable] = condition.test.assumed_value()
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
                if condition.results.count(False) > condition.required_failures:
                    print("(Invariant) Failing variable: " + condition.variable)
                    return condition.variable
            time.sleep(1 / 60)
        for condition in self.postconds:
            if not condition.satisfied_in_reality():
                print("(Postcond) Failing variable: " + condition.variable)
                return condition.variable
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
            if not getattr(shm.system_status, dependency).get():
                return False
        return True
