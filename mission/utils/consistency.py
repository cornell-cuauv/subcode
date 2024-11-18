from collections import deque
from threading import Thread
from typing import Callable, Tuple, Any
import shm
from shm.base import ShmVar

class ConsistencyTracker:
    """Stores a conditions's results to track if it is consistently met.

    It is assumed that to start the condition is not consistently true. If out
    of some number of consecutive tests, the condition is met some number of
    times, the condition will be considered consistently satisfied. It remains
    consistently satisfied until some number of tests fail out of some number of
    consecutive tests, at which point it is no longer considered consistently
    satisfied.
    """

    def __init__(self,
                 count_true: Tuple[int, int],
                 count_false: Tuple[int, int], default : bool):
        """
        Creates a ConsistencyTracker.

        Args:
            count_true:     how many successes out of how many tests turn the reult True
            count_false:    how many failures out of how many tests turn the result False
        
        These numbers are provided as two tuples, the first number of each being how
        many tests must have a certain result and the second being the total number
        of consecutive tests the results of which are stored at any given time.
        """
        self.results = deque([], maxlen = max(count_true[1], count_false[1]))
        self.count_true = count_true
        self.count_false = count_false
        self.consistent = default
    
    def update(self, result : bool) -> bool:
        """
        Log the result of a new test. Returns an updated verdict on if the
        condition is consistently met.
        """
        self.results.append(result)
        true_window = list(self.results)[:self.count_true[1]]
        if true_window.count(True) > self.count_true[0]:
            self.consistent = True
        false_window = list(self.results)[:self.count_false[1]]
        if false_window.count(False) > self.count_false[0]:
            self.consistent = False
        return self.consistent
    
    def clear(self):
        """
        Resets this ConsistentTracker's internal state.
        """
        self.results.clear()
        self.consistent = False

def ConsistencyFunction(tracker: ConsistencyTracker):
    def wrapper(func):
        def consistent(*args, **kwargs):
            return tracker.update(func(*args, **kwargs))
        return consistent
    return wrapper

class SHMConsistencyTracker:
    """
    Proactively tracks if a condition on a SHM group is consistently met.
    """
    def __init__(self,
                 group : Any,
                 test : Callable[[Any], bool],
                 count_true : Tuple[int, int],
                 count_false : Tuple[int, int] = None,
                 default : bool = False):
        """
        Creates a SHMConsistencyTracker. Initializing a SHMConsistencyTracker
        object starts a daemon thread which monitors the relevant SHM group.

        Args:
            group:          the SHM group on which the test will be performed
            test:           the test itself, to be called with the SHM group as input
            count_true:     how many successes out of how many tests turn the result True
            count_false:    how many failures out of how many tests turn the result False
            default:        what state the tracker is set to.
        """
        
        self.consistent : bool = default
        """A boolean determining if the test is consistently passing."""

        self.last_state = None
        """The state of the SHM group the last time the test passed.
              > Say the SHM group is red_buoy_results and the test determines if the
                buoy is visible. If it is not visible, you may want to use the position
                at which it was last seen since it likely will not have moved too far.
                The last_state property will contain the entire red_buoy_results SHM
                group at the time the buoy was last visible."""

        if not count_false:
            count_false = count_true

        def thread():
            tracker = ConsistencyTracker(count_true, count_false, default)
            watcher = shm.watchers.watcher()
            watcher.watch(group)

            while True:
                state = group.get()
                test_result = test(state)
                self.consistent = tracker.update(test_result)
                if test_result:
                    self.last_state = state
                watcher.wait()

        Thread(target=thread, daemon=True).start()


