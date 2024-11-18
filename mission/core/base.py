import sys
from abc import ABC
from types import CoroutineType
from collections import defaultdict

import shm
from mission import runner

class AsyncBase(ABC):
    """Useful base class for missions which employ coroutine chaining.

    A mission which employs chaining is broken down into multiple async
    functions each representing a sub-task of the mission. Each of these
    functions completes by returning a coroutine object made from the next such
    function which should be executed.

    As a trivial example, consider a mission which must submerge the sub and
    then move it forward. That mission could look like this:

    ```
    async def submerge(self):
        await depth(1.5)
        return self.move_forward()

    async def move_forward(self):
        await move_x(3)
        return None
    ```

    When submerge completes, it calls move_forward, creating a coroutine object.
    It returns that coroutine object. This AsyncBase instance then calls the
    returned coroutine made from move_forward, which eventually returns None.
    That signals to this instance that the mission is complete, so no more
    coroutines are called.
    """
    
    def run(self, name : str = None, debug : bool = False) -> None:
        """
        Use the mission runner to run the mission.
        
        Args:
            name:   The name of the mission.
            debug:  Whether to print messages out to stdout.
        """
        self.mission_name = (name if name is not None
                else f'{type(self).__name__}')
        if not hasattr(self, 'first_task'):
            raise AttributeError("You must set self.first_task.")
        
        transitions = []

        async def mission_chainer(coroutine):
            self.run_on_start()
            while type(coroutine) == CoroutineType:
                if debug:
                    print('>>> ' + coroutine.__name__)
                self.run_on_coroutine_begin(f"{coroutine}")
                previous_coroutine_name = coroutine.__name__
                coroutine = await coroutine
                if type(coroutine) == CoroutineType:
                    transitions.append((previous_coroutine_name,
                            coroutine.__name__))
                self.run_on_coroutine_end(f"{coroutine}")
            
            self.run_on_end()
            if debug:
                print(f'Mission result: {coroutine}')
            
            result_name = ('Success' if coroutine is True else
                    'Failure' if coroutine is False else 'Finish')
            transitions.append((previous_coroutine_name, result_name))
            flowchart = {}
            for i, transition in enumerate(transitions):
                if transition in flowchart:
                    flowchart[transition].append(i)
                else:
                    flowchart[transition] = [i]

            flowchart_code = "flow: down;state Start: {background-color: blue;};state Success: {background-color: green;};state Failure: {background-color: red;};state Finish: {background-color: blue;};"
            for (tail, head), numbers in flowchart.items():
                flowchart_code += f"{tail} '{', '.join(str(n) for n in numbers)}' -> {head};"
            html = '<!doctype html><html><head><title>jssm-viz example</title><script defer type="text/javascript" src="../../../repo/mission/jssm-viz.iife.js"></script><script defer type="text/javascript">window.onload = async () => {const ExMachine = `' + flowchart_code + '`;document.getElementById("tgt").innerHTML = await window.jssm_viz.fsl_to_svg_string(ExMachine);}</script></head><body><div id="tgt"></div></body></html>'
            with open(f'{shm.active_mission.log_path.get()}/flowchart.html', 'w') as f:
                f.write(html)
            

        if len(sys.argv) == 1:
            first_coroutine = self.first_task
        else:
            if hasattr(self, sys.argv[1]):
                first_coroutine = getattr(self, sys.argv[1])()
            else:
                print(f'Mission contains no method called "{sys.argv[1]}".')
                sys.exit(1)

        transitions.append(('Start', first_coroutine.__name__))
        runner.run(mission_chainer(first_coroutine), self.mission_name)

    async def run_headless(self, debug : bool = False):
        """
        Run the mission without using the mission runner.

        Since not using the mission runner means ignoring the mission lock and
        other dangerous things, you should never call this method yourself. See
        master_common.py for how it can be used safely in the context of a
        master mission which has already invoked the mission runner.
        """
        self.run_on_start()
        coroutine = self.first_task
        while type(coroutine) == CoroutineType:
            if debug:
                print(coroutine.__name__)
            self.run_on_coroutine_begin(f"{coroutine}")
            coroutine = await coroutine       
            self.run_on_coroutine_end(f"{coroutine}")
        self.run_on_end()
        if debug:
            print(f'Mission result: {coroutine}')
        return coroutine

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

