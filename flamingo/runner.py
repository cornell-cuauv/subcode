#!/usr/bin/env python3

import sys
import importlib
import time
import signal

import shm
from mission.framework.primitive import Zero

# Check that there is exactly one additional argument.
if len(sys.argv) != 2:
    print("Error: Provide the name of the mission file (wiithout the .py) as an argument.")
    sys.exit()

# Import the mission file.
try:
    mission = importlib.import_module("missions." + sys.argv[1])
except:
    print("Error: Something went wrong when importing " + sys.argv[1] + ".")
    sys.exit()


# Clean up on interrupt.
vision_modules_state = shm.vision_modules.get()
settings_control_state = shm.settings_control.get()
navigation_settings_state = shm.navigation_settings.get()

def handle_interrupt(sig, frame):
    Zero()()
    shm.vision_modules.set(vision_modules_state)
    shm.settings_control.set(settings_control_state)
    shm.navigation_settings.set(navigation_settings_state)
    sys.exit(0)

signal.signal(signal.SIGINT, handle_interrupt)

# Find all state variables and their initial values if known.
def find_theoretical_starting_state():
    starting_state = {}
    if hasattr(mission, 'initial_state'):
        for var, val in mission.initial_state.items():
            starting_state[var] = val
    for condition in mission.goal:
        if condition.variable not in starting_state:
            starting_state[condition.variable] = None
    for action in mission.actions:
        for condition in action.preconds + action.invariants + action.postconds:
            if condition.variable not in starting_state:
                starting_state[condition.variable] = None
    return starting_state

# Evaluate shm state variables to find the real starting state.
def find_real_starting_state():
    starting_state = find_theoretical_starting_state()
    for variable in starting_state:
        if "." in variable:
            group, _, name = variable.partition(".")
            starting_state[variable] = getattr(getattr(shm, group), name).get()
    return starting_state

# Check if a state satisfies a list of conditions.
def conditions_satisfied_in_state(conditions, state):
    for condition in conditions:
        if not condition.test.satisfied_in_state(condition.variable, state):
            return False
    return True

class SearchNode:
    def __init__(self, state, plan):
        self.state = state
        self.plan = plan

# Find a list of actions to get from a starting state to the mission's goal.
def solve(starting_state):
    queue = [SearchNode(starting_state, [])]
    while len(queue) > 0:
        node = queue.pop(0)
        if conditions_satisfied_in_state(mission.goal, node.state):
            return node.plan
        for action in mission.actions:
            if action.dependencies_functioning():
                if conditions_satisfied_in_state(action.preconds, node.state) and not conditions_satisfied_in_state(action.postconds, node.state):
                    queue.append(SearchNode(action.state_after_action(starting_state.keys()), node.plan + [action]))

# Find a plan to get from the real starting state to the mission's goal and execute it, one action at a time.
def find_and_execute_plan():
    starting_state = find_real_starting_state()
    print("Current state: " + str(starting_state))
    plan = solve(starting_state)
    print("Plan identified: " + ", ".join([action.name for action in plan]))
    for action in plan:
        print("Executing action: " + action.name)
        result = action.execute()
        if not result:
            Zero()()
            action.run_on_failure()
            Zero()()
            return False
    return True

while not find_and_execute_plan():
    time.sleep(0.1)
