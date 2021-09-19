#!/usr/bin/env python3

import sys
import importlib
import threading
import time

# Check that there is exactly one additional argument.
if len(sys.argv) != 2:
    print("Provide the name of the mission file as an argument.")
    sys.exit()

# Import the mission file.
try:
    mission = importlib.import_module(sys.argv[1])
except:
    print("Something went wrong when importing " + sys.argv[1] + ".")
    sys.exit()

# Is a certain set of conditions satisfied in a given state?
def conditions_met(conditions, current_state):
    for condition in conditions:
        if not current_state[condition]:
            return False
    return True

# What state is guaranteed after a given action is completed successfuly?
def state_after_action(action, state_variables):
    state = {}
    for variable in state_variables:
        state[variable] = False
    for condition in action.postconditions:
        state[condition] = True
    return state

# Use a BFS to identify a plan (defined as a list of sequential actions) which will take the sub from the given starting state to the mission's goal.
# TODO: If it is impossible to reach the goal, the BFS will never terminate. This could be solved through a cutoff procedure, or perhaps static mission testing could determine beforehand if a mission is impossible.
def solve(starting_state, mission):
    queue = [{"state": starting_state, "plan": []}]
    while len(queue) > 0:
        node = queue.pop(0)
        if node["state"][mission.goal]:
            return node["plan"]
        for action in mission.actions:
            if conditions_met(action.preconditions, node["state"]) and not conditions_met(action.postconditions, node["state"]):
                queue.append({"state": state_after_action(action, mission.state), "plan": node["plan"] + [action]})

# Run the code associated with an action, checking its invariants continuously and its postconditions upon completion.
# Returns the success of the action: False if the invariants or postconditions are violated and True otherwise.
def execute_action(action):
    print("Executing " + action.name)
    action_thread = threading.Thread(target=action.function)
    action_thread.start()
    while action_thread.is_alive():
        for condition in action.invariants:
            if not condition():
                return False
        time.sleep(0.1) # This is arbitrary and could be moved to config.
    for condition in action.postconditions:
        if not condition():
            return False
    return True

# Identify the state of the mission, find a plan to the goal state, and then execute said plan.
# Return the success of the selected plan: True if the goal state is achieved and False if an action fails along the way.
def find_and_execute_plan(mission):
    # Evaluate the true starting state.
    starting_state = {}
    for variable in mission.state:
        starting_state[variable] = variable()
    print("Starting state: " + ", ".join([str(value) for key, value in starting_state.items()]))

    # Identify a mission plan.
    plan = solve(starting_state, mission)
    print("Executing plan: " + ", ".join([action.name for action in plan]))

    # Run the mission until an action fails or the plan is completed successfully.
    for action in plan:
        result = execute_action(action)
        if not result:
            return False
    return True

# Attempt to complete the mission until successful.
completed = False
while not completed:
    completed = find_and_execute_plan(mission)
