import threading
from abc import ABC
from types import CoroutineType
from typing import Tuple, Callable, List, Any
from collections import deque
import time
import asyncio

import shm
from mission.framework.primitive import zero
from mission import runner

class AsyncBase(ABC):
    """Useful base class for missions which employ coroutine chaining.

    A mission which employs chaining is broken down into multiple async
    functions each representing a sub-task of the mission. Each of these
    functions completes by returning a coroutine object made from the next such
    function which should be executed.

    As a trivial example, consider a mission which must submerge the sub and
    then move it forward. That mission could look like this:

    async def submerge(self):
        await depth(1.5)
        return self.move_forward()

    async def move_forward(self):
        await move_x(3)
        return None

    When submerge completes, it calls move_forward, creating a coroutine object.
    It returns that coroutine object. This AsyncBase instance then calls the
    returned coroutine made from move_forward, which eventually returns None.
    That signals to this instance that the mission is complete, so no more
    coroutines are called.
    """
    def run(self, name : str = None):
        """Use the mission runner to run the mission."""
        self.mission_name = name if name is not None else f'{type(self).__name__}'
        if not hasattr(self, 'first_task'):
            raise AttributeError("You must set self.first_task.")

        async def mission_chainer(coroutine):
            self.run_on_start()
            while type(coroutine) == CoroutineType:
                self.run_on_coroutine_begin(f"{coroutine}")
                coroutine = await coroutine 
                self.run_on_coroutine_end(f"{coroutine}")
            self.run_on_end()

        runner.run(mission_chainer(self.first_task), self.mission_name)

    async def run_headless(self):
        """Run the mission without using the mission runner.

        Since not using the mission runner means ignoring the mission lock and
        other dangerous things, you should never call this method yourself. See
        master_common.py for how it can be used safely in the context of a
        master mission which has already invoked the mission runner.
        """
        self.run_on_start()
        coroutine = self.first_task
        while type(coroutine) == CoroutineType:
            self.run_on_coroutine_begin(f"{coroutine}")
            coroutine = await coroutine       
            self.run_on_coroutine_end(f"{coroutine}")
        self.run_on_end()

    def run_on_start(self):
        """Runs before the mission starts. Meant to be overridden."""
        pass
    
    def run_on_end(self):
        """Runs after the mission ends. Meant to be overridden."""
        pass

    def run_on_coroutine_begin(self, name):
        """Runs before each chained coroutine. Meant to be overridden."""
        pass

    def run_on_coroutine_end(self, name):
        """Runs after each chained coroutine. Meant to be overridden."""
        pass

class ConsistencyTracker:
    """Stores a conditions's results to track if it is consistently met.

    It is assumed that to start the condition is not consistently true. If out
    of some number of consecutive tests, the condition is met some number of
    times, the condition will be considered consistently satisfied. It remains
    consistently satisfied until some number of tests fail out of some number of
    consecutive tests, at which point it is no longer considered consistently
    satisfied.

    These numbers are provided as two tuples, the first number of each being how
    many tests must have a certain result and the second being the total number
    of consecutive tests the results of which are stored at any given time.
    
    __init__ Arguments:
    count_true  -- how many successes out of how many tests turn the reult True
    count_false -- how many failures out of how many tests turn the result False
    """

    def __init__(self, count_true: Tuple[int, int],
            count_false: Tuple[int, int]):
        self.results = deque([], maxlen = max(count_true[1], count_false[1]))
        self.count_true = count_true
        self.count_false = count_false
        self.consistent = False
    
    def update(self, result : bool) -> bool:
        """Log the result of a new test.

        Returns an updated verdict on if the condition is consistently met.
        """
        self.results.append(result)
        true_window = list(self.results)[:self.count_true[1]]
        if true_window.count(True) > self.count_true[0]:
            self.consistent = True
        false_window = list(self.results)[:self.count_false[1]]
        if false_window.count(True) > self.count_false[0]:
            self.consistent = False
        return self.consistent
    
    def clear(self):
        """Resets this ConsistentTracker's internal state."""
        self.results.clear()
        self.consistnt = False

class SHMConsistencyTracker:
    """Proactively tracks if a condition on a SHM group is consistently met.

    Initializing a SHMConsistencyTracker object starts a daemon thread which
    monitors the relevant SHM group.
    
    __init__ Arguments:
    group       -- the SHM group on which the test will be performed
    test        -- the test itself, to be called with the SHM group as input
    count_true  -- how many successes out of how many tests turn the result True
    count_false -- how many failures out of how many tests turn the result False

    Properties:
    consistent -- if the test is consistently passing
    last_state -- the state of the SHM group the last time the test passed
        > Say the SHM group is red_buoy_results and the test determines if the
        buoy is visible. If it is not visible, you may want to use the position
        at which it was last seen since it likely will not have moved too far.
        The last_state property will contain the entire red_buoy_results SHM
        group at the time the buoy was last visible.
    """
    def __init__(self, group : Any, test : Callable[[Any], bool],
            count_true : Tuple[int, int], count_false : Tuple[int, int] = None):
        self.consistent = False
        self.last_state = None

        if not count_false:
            count_false = count_true

        def thread():
            tracker = ConsistencyTracker(count_true, count_false)
            watcher = shm.watchers.watcher()
            watcher.watch(group)

            while True:
                watcher.wait()
                state = group.get()
                test_result = test(state)

                self.consistent = tracker.update(test_result)
                if test_result:
                    self.last_state = state

        threading.Thread(target=thread, daemon=True).start()

