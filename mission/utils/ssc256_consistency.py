from collections import deque
from threading import Thread
import time
import shm
from scipy import stats
from typing import Any, Callable
import math

# TODO: handle guess positions, shm wrapper, shm access to gx accel
# Possibly make an invalid state for things that need it (result, guess, etc)
# Try to implement a confidence heuristic for ints, but hard with no context
# probably don't need nanosecond resolution but we do need more than second resolution
class ConsistentTargeting:
  """ Keeps track of a constantly updated data value and attempts to stabilize it.

  Currently incomplete and should only be used to keep track of multiple target detections

  Arguments:
  history_size     -- the number of past frames the system should keep (generally larger is better)
  data_type        -- the string representation of the data type to keep track of (currently, "int", 
                      "bool", "pos" are implemented for integers, booleans and positional values, respectively) 
  default_val      -- a default value for the data type. Only used on initialization and when data is cleared
  valid_count      -- (only for booleans) the number of True's needed for the system to output True
  num_detections   -- (only for positions) the number of "centers" to keep track of. Each instance of a target 
                      should get a center (so if you want to keep track of 12 bottles, this should be 12).
  smoothing_factor -- (currently unused) the smoothing rate for exponential smoothing and point mean updates.
  """
  # data_type is one of [int, bool, pos (int * int)]
  # for exponential smoothing, smoothing = 1 means trust current data completely
  # valid_count is for booleans
  def __init__(self, history_size : int, data_type : str, default_val=False, valid_count=False, num_detections=1, smoothing_factor=1):
    # Note: As outlier detection is currently dependent on a constant, this shouldn't be used until you get close enough that the 
    # distance between classifications becomes meaningful
    self.track_outliers = True

    self.history = deque([], maxlen=history_size)
    self.valid_history = deque([],maxlen=history_size)
    self.confidence_history = deque([],maxlen=history_size)
    self.classify_history = deque([],maxlen=history_size)
    self.valid_count = valid_count or history_size // 2 + 1
    self.timestamps = deque([], maxlen=history_size)
    self.history_size = history_size
    self.n = 1 if data_type == "bool" else num_detections
    self.data_type = data_type
    self.default_val = default_val
    if data_type == "int":
      self.default = [default_val] * self.n or [0] * self.n
      self.result = [0] * self.n
    elif data_type == "bool":
      self.default = [default_val]
      self.result = [False]
    elif data_type == "pos":
      self.default = [default_val or (0,0)] * self.n
      self.result = [(0,0)] * self.n
    self.metadata = [None] * self.n
    self.guess = [self.default] * self.n
    self.confidence = [0] * self.n
    self.classify_valid = [False] * self.n
    self.thresholds = [10000] * self.n
    self.smoothing = smoothing_factor
    self.last_update = time.time_ns()

  # Internal math to normalize probabilities 
  def normalize_confidence_h(self, idx):
    if not (self.confidence_history > 3):
      return
    mask = [i == idx for i in self.classify_history]
    # Linear interpolation to rescale probabilities
    a = min(self.confidence_history[mask])
    b = max(self.confidence_history[mask])
    if (a <= 0.01 and b >= 0.99):
      return
    if abs(a - b) <= 0.01:
      for i in range(len(self.confidence_history[mask])):
        self.confidence_history[i] = 1
    else:
      for i in range(len(self.confidence_history)):
        if mask[i]:
          self.confidence_history[i] = (self.confidence_history[i]-a)/(b-a)
  def point_mean(self,lst):
    # Disabling KMeans for now - just going to base it off of last detection
    # x_total = 0
    # y_total = 0
    # if len(lst) == 0:
    #     return (-1,-1)
    # for i in range(len(lst)):
    #   (x,y) = lst[i]
    #   if i == len(lst) - 1:
    #     x_total += x * 4
    #     y_total += y * 4
    #   else: 
    #     x_total += x 
    #     y_total += y
    # return (x_total/(len(lst) + 3), y_total/(len(lst) + 3))
    if len(lst) == 0:
      return (-1,-1)
    return lst[-1]
  def update(self, data_lst, valid_lst="default", metadata_lst=[]):
    """ Update the system with new data. 

    Arguments:
    data_lst  -- the data to update the system with. Should be a list of values (list of coordinate pairs for positions)
             Note that each element will count as one update to the system, so len(data) past datum will be evicted from history when full. 
    valid_lst -- list of booleans: True if data is valid (for taking true negatives into account)
    The lengths of the two lists should match.
    """
    print(self.classify_history)
    if valid_lst == "default":
      valid_lst = [True] * len(data_lst)
    l = len(data_lst)
    if l != len(valid_lst):
      raise ValueError("List lengths do not match: data list has length " + str(l) + " and valid list has length " + str(len(valid_lst)))
    if l != len(metadata_lst) and len(metadata_lst) != 0:
      raise ValueError("Incorrect metadata list length, is " + str(len(metadata_lst) + " but should be either 0 or " + str(l) + ", please pad with Nones"))
    metadata_valid = l == len(metadata_lst)
    for detection_idx in range(l):
      data = data_lst[detection_idx]
      valid = valid_lst[detection_idx]
      md =  metadata_lst[detection_idx] if metadata_valid else None
      self.history.append(data)
      self.timestamps.append(time.time_ns())
      self.valid_history.append(valid)
      if self.data_type == "bool":
          self.result = [self.history.count(True) >= self.valid_count]
          self.confidence = self.history.count(True) / self.history.length
          self.guess = [self.history.count(True) >= self.history.count(False)]
      elif self.data_type == "int":
          if valid:
              self.result = self.smoothing * data + (1-self.smoothing)*self.result
          self.confidence = 1 #TODO
          s, i, _, _, _ = stats.linregress(self.timestamps[self.valid_history], self.history[self.valid_history])
          self.guess = s * time.time_ns + i
      elif self.data_type == "pos":
          #TODO: also add rotations
          #TODO: temporarily unused
          ax = getattr(shm.gx4,"accelx").get()
          ay = getattr(shm.gx4,"accely").get()
          az = getattr(shm.gx4,"accelz").get()
          gx_mag = (ax**2 + ay**2 + az**2) ** (1/2)
          base_accel = 1
          adaptive_smooth = self.smoothing * max(min(1,gx_mag/base_accel),0.5)
          
          if len(self.classify_history) == self.history_size:
            to_be_removed = self.classify_history[0]
          else:
            to_be_removed = -1

          if not valid:
            self.classify_history.append(-1)
          if valid: 
            # classified flag
            c = False
            min_dist = 0
            min_dist_classify = -1
            for i in range(self.n):
              if not self.classify_valid[i]:
                continue
              x_old, y_old = self.result[i]
              (x_new, y_new) = data
              delta = (x_new - x_old)**2 + (y_new - y_old)**2
              if delta > self.thresholds[i] and self.track_outliers:
                continue
              # update minimum distance center if no distance has been recorded yet or if the distance 
              # to the current center is less than the distance to the previous minimum distance center
              if not c or min_dist > delta:
                min_dist = delta
                c = True
                min_dist_classify = i
            # If classified, update classifications
            if c:
              cs = []
              self.classify_history.append(min_dist_classify)
              for j in range(len(self.classify_history)):
                if self.classify_history[j] == min_dist_classify:
                    cs.append(self.history[j])
              self.result[min_dist_classify] = self.point_mean(cs)
              self.metadata[min_dist_classify] = md
          # Clean up stale classifications
          if self.classify_valid[to_be_removed] and to_be_removed != -1:
            # num last seen recently. Slightly magic number-y, but it has to be at least num_detections 
            # because each of the separate detections will count as their own update.
            nlsr = min(math.floor(len(self.classify_history) / 2) + len(self.result), len(self.classify_history))
            #jank way to test if there has been a classification of evicted classification in the nlsr most recent frames
            try:
              self.classify_history.index(to_be_removed,len(self.classify_history) - nlsr, len(self.classify_history) - 1)
              continue
            except:
              self.classify_valid[to_be_removed] = False
              for j in range(len(self.classify_history)):
                if self.classify_history[j] == to_be_removed:
                    self.classify_history[j] = -1
          if valid:     
            # if an outlier for all current centers,
            if not c:
              for i in range(self.n):
                # either make a new center if possible
                if self.classify_valid[i] == False:
                  self.classify_history.append(i)
                  self.result[i] = data
                  self.metadata[i] = md
                  c = True
                  self.classify_valid[i] = True
                  break
              # or classify as an outlier
              if not c:
                  self.classify_history.append(-1)
            
            #self.result = (adaptive_smooth * x_new + (1-adaptive_smooth)*x_old, adaptive_smooth*y_new + (1-adaptive_smooth)*y_old)
          
            
          #if delta == 0 or gx_mag == 0:
          #    self.confidence = 1
          #    c, r = self.confidence_value()
          #    self.confidence = c
          #else:
          #    self.confidence = 1/(delta/gx_mag if delta >= gx_mag else gx_mag/delta)

          #x_lst = []
          #y_lst = []
          #for i in self.history:
          #  x_lst.append(i[0])
          #  y_lst.append(i[1])
          #sx, ix, _, _, _ = stats.linregress(self.timestamps, x_lst)
          #sy, iy, _, _, _ = stats.linregress(self.timestamps, y_lst)
          #self.guess = (sx * time.time_ns() + ix, sy * time.time_ns() + iy)
          # TODO: Temporary
          self.guess = [(0,0)]
      # TODO: Temporary
      self.confidence_history.append(1)
      if valid:
          self.last_update = time.time_ns()

  def clear(self):
    """ Resets the system to default.
    """
    self.track_outliers = True

    self.history = deque([], maxlen=self.history_size)
    self.valid_history = deque([],maxlen=self.history_size)
    self.confidence_history = deque([],maxlen=self.history_size)
    self.classify_history = deque([],maxlen=self.history_size)
    self.timestamps = deque([], maxlen=self.history_size)
    self.history_size = self.history_size
    self.default_val = self.default_val
    if self.data_type == "int":
      self.default = [self.default_val] * self.n or [0] * self.n
      self.result = [0] * self.n
    elif self.data_type == "bool":
      self.default = [self.default_val]
      self.result = [False]
    elif self.data_type == "pos":
      self.default = [self.default_val or (0,0)] * self.n
      self.result = [(0,0)] * self.n
    self.guess = [self.default] * self.n
    self.confidence = [0] * self.n
    self.classify_valid = [False] * self.n
    self.thresholds = [10000] * self.n
    self.last_update = time.time_ns()
    self.metadata = [None] * self.n
    
  def value(self):
    """ Returns the system's (stabilized) data.
    """
    return self.result
  def valid(self):
    """ Returns whether each of the data values are valid.
    """
    return self.classify_valid
  def get_metadata(self):
    """ Returns metadata stored with each detection.
    """
    return self.metadata
  def confidence_value(self): 
    """ Sort of placeholder for now, first value is proportional to how long it's been
        since the system was last updated
    """
    return (self.confidence - (self.decay_time() / 1000000000), self.result)
  def last_data(self):
    """ Returns the last valid data sent to the system
    """
    for i in range(len(self.valid_history)-1, 0, -1):
      if self.valid_history[i]:
        return self.history[i]
    return self.default[0]
  def guess_val(self):
    """ Placeholder, do not use
    """
    return self.guess
  def decay_time(self):
    """ Returns the time (in nanoseconds) since the last data update to the system.
        Can potentially use this to track if SHM broke if using the SHM wrapper.
    """
    return time.time_ns() - self.last_update
class SHMConsistentTargeting:
  """ SHM wrapper for the module above. Arguments are all the same. 
      Currently extremely laggy, drops the framerate of the vision module attached to 
      1 fps. Will investigate in the future.
  """
  def __init__(self, group : Any, test : Callable[[Any], bool],
            history_size : int, data_type : str, default_val=False, valid_count=False, num_detections=1, smoothing_factor=1):
        def thread():
            tracker = ConsistentTargeting(history_size, data_type, default_val, valid_count, num_detections, smoothing_factor)
            watcher = shm.watchers.watcher()
            watcher.watch(group)

            while True:
                state = group.get()
                test_result = test(state)
                tracker.update(test_result)
                self.result = tracker.value()
                self.confidence = tracker.confidence_value()
                self.last_data = tracker.last_data()
                self.guess = tracker.guess_val()
                self.decay_time = tracker.decay_time()
                watcher.wait()

        Thread(target=thread, daemon=True).start()

