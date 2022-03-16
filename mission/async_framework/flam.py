from typing import Dict, Set

from flamingo2.state import State
from flamingo2.action import Action
from flamingo2.runner import Runner

async def flamingo_mission(initial_state : State, goals : Dict[State, int],
        actions : Set[Action]):
    runner = Runner(initial_state, goals, actions)
    await runner.run()
