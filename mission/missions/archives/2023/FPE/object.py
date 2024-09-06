from mission.framework.consistency import SHMConsistencyTracker
import shm

class ObjectBase:
    """
    Object: turns the parameters of shm bins into
    standardized parameters that can be used by common
    functions. Represents an object with a center, area,
    and visibility heuristic.
    """

    def __init__(self, shm_bin):
        self.shm = shm_bin
        pass

    def area(self):
        """
        Returns: the area of the object.
        """

    def coordinates(self):
        """
        Returns: the normalized coordinates, as a
        tuple, of the object.
        """

    def is_visible(self):
        """
        Returns: True of the object is visible, false
        otherwise.
        """

class QualGate(ObjectBase):
    """
    QualGate: a qualification gate.
    """

    def __init__(self, shm_bin):
        super().__init__(shm_bin)
        self.tracker = SHMConsistencyTracker(
            self.shm, lambda bin: bin.middle_visible == 1, (9, 10), (9, 10), False)

    def area(self):
        return (self.left_area() + self.right_area()) / 2

    def coordinates(self):
        return (self.shm.middle_x.get(),
                self.shm.middle_y.get())

    def is_visible(self):
        return self.shm.middle_visible.get() == 1

    def left_area(self):
        return self.shm.leftmost_len.get()

    def right_area(self):
        return self.shm.rightmost_len.get()

    def consistency_tracker(self):
        """
        Returns: a consistency tracker of this object.
        """
        return self.tracker

class Buoy(ObjectBase):
    """
    Buoy: a buoy.
    """

    def __init__(self, shm_bin):
        super().__init__(shm_bin)
        self.tracker = SHMConsistencyTracker(
            self.shm, lambda bin: bin.heuristic_score == 1, (4, 5), (9, 10), False)

    def area(self):
        return self.shm.area.get()

    def coordinates(self):
        return (self.shm.center_x.get(), self.shm.center_y.get())

    def is_visible(self):
        return self.shm.heuristic_score.get() == 1

    def consistency_tracker(self):
        """
        Returns: a consistency tracker of this object.
        """
        return self.tracker

class Path(ObjectBase):
    """
    Path: a path.
    """

    def __init__(self, shm_bin):
        super().__init__(shm_bin)
        print(self.shm.visible.get())
        self.tracker = SHMConsistencyTracker(
            self.shm, lambda bin: bin.visible == 1, (9, 10), (9, 10), False)

    def area(self):
        return self.shm.area.get()

    def coordinates(self):
        return (self.shm.center_x.get(), self.shm.center_y.get())

    def is_visible(self):
        return self.shm.visible.get() == 1

    def angle(self):
        return self.shm.angle.get()

    def consistency_tracker(self):
        """
        Returns: a consistency tracker of this object.
        """
        return self.tracker

class CompGate(ObjectBase):
    def __init__(self, shm_bin):
        super().__init__(shm_bin)
        self.tracker = SHMConsistencyTracker(
            self.shm, lambda bin: bin.leftmost_visible == 1 and bin.middle_visible == 1 and bin.rightmost_visible == 1, (9, 10), (9, 10), False)

    def area(self):
        return 0 # TODO

    def coordinates(self):
        x = (self.shm.leftmost_x.get() + self.shm.rightmost_x.get()) / 2
        y = self.shm.leftmost_y.get()
        return (x, y)

    def is_visible(self):
        return self.tracker.consistent

    def left_area(self):
        return self.shm.leftmost_len.get()

    def right_area(self):
        return self.shm.rightmost_len.get()

    def consistency_tracker(self):
        """
        Returns: a consistency tracker of this object.
        """
        return self.tracker

class CompGateLeft(ObjectBase):
    def __init__(self, shm_bin):
        super().__init__(shm_bin)
        self.tracker = SHMConsistencyTracker(
            self.shm, lambda bin: bin.leftmost_visible == 1 and bin.middle_visible == 1, (9, 10), (9, 10), False)

    def area(self):
        return 0 # TODO

    def coordinates(self):
        x = (self.shm.leftmost_x.get() + self.shm.middle_x.get()) / 2
        y = self.shm.leftmost_y.get()
        return (x, y)

    def is_visible(self):
        return self.tracker.consistent

    def left_area(self):
        return self.shm.leftmost_len.get()

    def right_area(self):
        return self.shm.middle_len.get()

    def consistency_tracker(self):
        """
        Returns: a consistency tracker of this object.
        """
        return self.tracker

class Glyph(ObjectBase):
    def __init__(self, shm_bin):
        super().__init__(shm_bin)
        self.tracker = SHMConsistencyTracker(
            self.shm, lambda bin: bin.visible == 1, (9, 10), (9, 10), False)
        
    def area(self):
        print(self.shm.area.get())
        return self.shm.area.get()
    
    def coordinates(self):
        return (self.shm.center_x.get(), self.shm.center_y.get())

    def error(self):
        return self.shm.error.get()
    
    def is_visible(self):
        return self.tracker.consistent
    
    def consistency_tracker(self):
        """
        Returns: a consistency tracker of this object.
        """
        return self.tracker

class GlyphIndicator(ObjectBase):
    def __init__(self, shm_bin):
        self.shm = shm_bin
        self.tracker = SHMConsistencyTracker(
            self.shm, lambda bin: bin.heuristic > 0, (1, 3), (3, 3), False)
    
    def is_visible(self):
        return self.tracker.consistent
    
    def consistency_tracker(self):
        return self.tracker

class Yolo(ObjectBase):
    """
    Yolo: a yolo object.
    """

    def __init__(self, shm_bin):
        super().__init__(shm_bin)
        self.tracker = SHMConsistencyTracker(
            self.shm, lambda bin: bin.visible == 1, (4, 5), (9, 10), False)

    def angle(self):
        return self.shm.angle.get()

    def area(self):
        return self.shm.area.get()

    def coordinates(self):
        return (self.shm.center_x.get(), self.shm.center_y.get())

    def is_visible(self):
        return self.shm.visible.get() == 1

    def consistency_tracker(self):
        """
        Returns: a consistency tracker of this object.
        """
        return self.tracker