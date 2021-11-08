#!/usr/bin/env python3

import sys
import importlib
import time
import signal

import shm
from mission.framework.primitive import Zero
from flamingo.framework import State, Condition

# Check that there is exactly one additional argument.
if len(sys.argv) != 2:
    print("Error: Provide the name of the mission file (wiithout the .py) as an argument.")
    sys.exit()

# Import the mission file.
try:
    mission = importlib.import_module("missions." + sys.argv[1])
except Exception as e:
    print("Error: Something went wrong when importing " + sys.argv[1] + ":")
    print(e)
    sys.exit()


# Clean up on interrupt.
vision_modules_state = shm.vision_modules.get()
settings_control_state = shm.settings_control.get()
navigation_settings_state = shm.navigation_settings.get()

def cleanup(*args):
    Zero()()
    shm.vision_modules.set(vision_modules_state)
    shm.settings_control.set(settings_control_state)
    shm.navigation_settings.set(navigation_settings_state)
    sys.exit(0)

signal.signal(signal.SIGINT, cleanup)

def find_starting_state():
    state = State()
    for action in mission.actions:
        for condition in action.preconds + action.invariants + action.postconds:
            if isinstance(condition, Condition):
                state.shm_values[condition.var] = condition.var.get()
    return state

class SearchNode:
    def __init__(self, state, plan):
        self.state = state
        self.plan = plan

# Find a list of actions to get from a starting state to the mission's goal.
def solve(starting_state):
    queue = [SearchNode(starting_state, [])]
    while len(queue) > 0:
        node = queue.pop(0)
        if node.state.satisfies_conditions(mission.goal):
            return node.plan
        for action in mission.actions:
            if action.dependencies_functioning():
                if node.state.satisfies_conditions(action.preconds) and not node.state.satisfies_conditions(action.postconds):
                    queue.append(SearchNode(action.state_after_action(node.state), node.plan + [action]))

# Find a plan to get from the real starting state to the mission's goal and execute it, one action at a time.
def find_and_execute_plan():
    starting_state = find_starting_state()
    print("Current state: " + str(starting_state))
    plan = solve(starting_state)
    print("Plan identified: " + ", ".join([action.name for action in plan]))
    for action in plan:
        print("Executing action: " + action.name)
        failing_var = action.execute()
        if failing_var:
            Zero()()
            action.run_on_failure(failing_var)
            Zero()()
            return False
    return True

while not find_and_execute_plan():
    time.sleep(0.1)
cleanup()
