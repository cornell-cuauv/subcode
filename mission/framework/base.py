from abc import ABC
from types import CoroutineType

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

