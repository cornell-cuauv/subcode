import threading
import time

import shm
import mission.runner as runner

class Condition:
    def __init__(self, variable, test):
        self.variable = variable
        self.test = test

    def satisfied_in_reality(self):
        if not "." in self.variable:
            return True
        group, _, name = self.variable.partition(".")
        real_value = getattr(getattr(shm, group), name).get()
        return self.test.satisfied_in_state(self.variable, {self.variable: real_value})

class Test:
    def assumed_value(self):
        return None
    
    def satisfied_in_state(self, state):
        return False

class EQ(Test):
    def __init__(self, val):
        self.val = val

    def assumed_value(self):
        return self.val
    
    def satisfied_in_state(self, variable, state):
        if state[variable] == None:
            return False
        return state[variable] == self.val

class GE(Test):
    def __init__(self, val):
        self.val = val

    def assumed_value(self):
        return self.val

    def satisfied_in_state(self, variable, state):
        if state[variable] == None:
            return False
        return state[variable] >= self.val

class LE(Test):
    def __init__(self, val):
        self.val = self.val

    def assumed_value(self):
        return self.val

    def satisfied_in_state(self, variable, state):
        if state[variable] == None:
            return False
        return state[variable] <= self.val

class TH(Test):
    def __init__(self, val, tolerance):
        self.val = val
        self.tolerance = tolerance

    def assumed_value(self):
        return self.val

    def satisfied_in_state(self, variable, state):
        if state[variable] == None:
            return False
        return abs(state[variable] - self.val) <= self.tolerance

class Action:
    def __init__(self, name, preconds, invariants, postconds, func):
        self.name = name
        self.preconds = preconds
        self.invariants = invariants
        self.postconds = postconds
        self.func = func

    def state_after_action(self, all_variables):
        state = {}
        for variable in all_variables:
            state[variable] = None
        for condition in self.postconds:
            state[condition.variable] = condition.test.assumed_value()
        return state
    
    def execute(self):
        action_thread = threading.Thread(target=runner.manual_args(self.func, {}))
        action_thread.start()
        while action_thread.is_alive():
            for condition in self.invariants:
                if not condition.satisfied_in_reality():
                    action_thread.stop()
                    print("Failing variable: " + condition.variable)
                    return False
            time.sleep(0.1)
        for condition in self.postconds:
            if not condition.satisfied_in_reality():
                return False
        return True
