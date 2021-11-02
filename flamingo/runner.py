#!/usr/bin/env python3

import sys
import importlib
import time
import shm

# Check that there is exactly one additional argument.
if len(sys.argv) != 2:
    print("Error: Provide the name of the mission file as an argument.")
    sys.exit()

# Import the mission file.
try:
    mission = importlib.import_module(sys.argv[1])
except:
    print("Error: Something went wrong when importing " + sys.argv[1] + ".")
    sys.exit()

# Find all state variables and their initial values if known.
def find_theoretical_starting_state():
    starting_state = {}
    if hasattr(mission, 'initial_state'):
        for condition in mission.initial_state:
            starting_state[condition.variable] = condition.test.assumed_value()
    for condition in mission.goal:
        if condition.variable not in starting_state:
            starting_state[condition.variable] = None
    for action in mission.actions:
        for condition in action.preconds + action.invariants + action.postconds:
            if condition.variable not in starting_state:
                starting_state[condition.variable] = None
    return starting_state

def find_real_starting_state():
    starting_state = find_theoretical_starting_state()
    for variable in starting_state:
        if "." in variable:
            group, _, name = variable.partition(".")
            starting_state[variable] = getattr(getattr(shm, group), name).get()
    return starting_state

def conditions_satisfied_in_state(conditions, state):
    for condition in conditions:
        if not condition.test.satisfied_in_state(condition.variable, state):
            return False
    return True

class SearchNode:
    def __init__(self, state, plan):
        self.state = state
        self.plan = plan

def solve(starting_state):
    queue = [SearchNode(starting_state, [])]
    while len(queue) > 0:
        node = queue.pop(0)
        if conditions_satisfied_in_state(mission.goal, node.state):
            return node.plan
        for action in mission.actions:
            if conditions_satisfied_in_state(action.preconds, node.state) and not conditions_satisfied_in_state(action.postconds, node.state):
                queue.append(SearchNode(action.state_after_action(starting_state.keys()), node.plan + [action]))

def find_and_execute_plan():
    starting_state = find_real_starting_state()
    print("Current state: " + str(starting_state))
    plan = solve(starting_state)
    print("Plan identified: " + ", ".join([action.name for action in plan]))
    for action in plan:
        print("Executing action: " + action.name)
        result = action.execute()
        if not result:
            return False
    return True

while not find_and_execute_plan():
    time.sleep(0.1)
