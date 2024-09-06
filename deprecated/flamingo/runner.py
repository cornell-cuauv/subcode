#!/usr/bin/env python3

import argparse
import importlib
import sys
import time
import signal

import shm
from mission.framework.primitive import Zero
from flamingo.framework import State, Comparison

def error(message):
    print('\033[1;31;40m' + str(message) + '\033[0m')

# Reset settings after termination.
def cleanup(*args):
    Zero()()
    shm.vision_modules.set(vision_modules_state)
    shm.settings_control.set(settings_control_state)
    shm.navigation_settings.set(navigation_settings_state)
    sys.exit(0)

# Evaluate all the relevent SHM variables.
def find_starting_state(mission):
    state = State()
    for action in mission.actions:
        for condition in action.preconds + action.invariants + action.postconds:
            if isinstance(condition, Comparison):
                state.shm_values[condition.var] = condition.var.get()
    return state

class SearchNode:
    def __init__(self, state, plan):
        self.state = state
        self.plan = plan

    def score(self, mission):
        total = 0
        for goal, value in mission.goals.items():
            if goal in self.state.flags:
                total += value
        return total

    def time(self):
        total = 0
        for action in self.plan:
            if action.time != None:
                total += action.time
        return total

# Find a list of actions to achieve as many goals as possible from a starting state.
def solve(starting_state, mission, max_actions, max_time):
    visited_states = set()
    queue = [SearchNode(starting_state, [])]
    best_plan = None
    best_plan_score = 0
    while len(queue) > 0:
        node = queue.pop(0)
        if node.state in visited_states or len(node.plan) > max_actions or node.time() > max_time:
            continue
        visited_states.add(node.state)
        if node.score(mission) > best_plan_score:
            best_plan = node.plan
            best_plan_score = node.score(mission)
        for action in mission.actions:
            if action.dependencies_functioning():
                if node.state.satisfies_conditions(action.preconds) and not node.state.satisfies_conditions(action.postconds):
                    queue.append(SearchNode(action.state_after_action(node.state), node.plan + [action]))
    if best_plan:
        return best_plan
    if args.max_actions == float("inf"):
        print("No plan was found to score any points.")
    else:
        print("No plan of at most " + str(args.max_actions) + " actions was found to score any points.")
    sys.exit(0)

# Find a plan and execute it, one action at a time.
def find_and_execute_plan(mission, max_actions, max_time):
    starting_state = find_starting_state(mission)
    plan = solve(starting_state, mission, max_actions, max_time)
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

def main(filename, max_actions, max_time):
    # Import the mission file.
    try:
        mission = importlib.import_module("missions." + filename)
    except Exception as e:
        error("Something went wrong when importing " + filename + ":")
        error(e)
        sys.exit()

    # Check that all actions specify time.
    if max_time != float("inf") and any([action.time == None for action in mission.actions]):
        error("Not all actions specify time, so --max-time will be ignored.")
        max_time = float("inf")

    # Clean up on interrupt.
    global vision_modules_state, settings_control_state, navigation_settings_state
    vision_modules_state = shm.vision_modules.get()
    settings_control_state = shm.settings_control.get()
    navigation_settings_state = shm.navigation_settings.get()
    
    signal.signal(signal.SIGINT, cleanup)
    
    while not find_and_execute_plan(mission, max_actions, max_time):
        time.sleep(0.1)
    cleanup()

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('filename')
    parser.add_argument('--max-actions', type=int, default=float("inf"))
    parser.add_argument('--max-time', type=int, default=float("inf"))
    args = parser.parse_args()
    
    main(args.filename, args.max_actions, args.max_time)
