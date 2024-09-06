from mission.framework.primitive import zero
from mission.framework.base import AsyncBase


class FPE_Task(AsyncBase):
    """
    FPE_Task: Upon object creation, performs a three-stage task.

    Stage 1 - Find.
    Stage 2 - Position.
    Stage 3 - Execute.
    """

    def __init__(self, object_1, action_1,
                 object_2, action_2, reference_2,
                 object_3, action_3, reference_3):
        """
        action_1, action_2, action_3 are the
        find, position, and execute actions on
        object_1, object_2, and object_3, respectively.

        object_1, object_2, object_3 are ObjectBase classes.

        actions are functions mentioned above.

        reference is an optional parameter given to action_2.
        """
        self.object_1, self.action_1 = object_1, action_1
        self.object_2, self.action_2, self.reference_2 = object_2, action_2, reference_2
        self.object_3, self.action_3, self.reference_3 = object_3, action_3, reference_3
        self.first_task = self.find(object_1, action_1)

    async def find(self, obj, action):
        """
        Find: finds [object] using find method [action].

        Because we are finding something, we are expected
        to find it at the end, otherwise we continue running.

        Moves onto the position stage when complete.
        """
        await zero()
        print("  -> find")
        await action(obj)
        return self.position(self.object_2, self.action_2, self.reference_2)

    async def position(self, obj, action, reference):
        """
        Position: given [object] is visible, perform position
        method [action].

        Depending on the action, object may or may not have
        to be visible.

        Moves on to the execute stage if successful, returns to
        find stage if failed.
        """
        await zero()
        print("  -> position")
        """
        Position tasks: given that the target object is on sight,
        move the submarine to a certain desired location relative
        to the object.

        Precondition: the object must visible.

        Returns: True if successful, False if unsuccessful.
        """
        success = await action(obj, reference)
        if success:
            return self.execute(self.object_3, self.action_3, self.reference_3)
        else:
            return self.find(self.object_1, self.action_1)

    async def execute(self, obj, action, reference):
        """
        Execute: given [object] is visible, perform execute
        method [action].

        Depending on the action, object may or may not have to
        be visible.

        FPE_Task exits if successful, returns to position stage if
        failed.
        """
        await zero()
        print("  -> execute")
        success = await action(obj, reference)
        if not success:
            return self.position(self.object_2, self.action_2, self.reference_2)
