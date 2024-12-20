import os
import shm
import cv2
from datetime import datetime

log_base_path = os.path.join(os.environ['CUAUV_LOG'], "current")

class VideoWriter:
    def __init__(self, direction, filename=None):
        if os.getenv('CUAUV_VEHICLE') == 'polaris':
            self.fourcc = cv2.VideoWriter_fourcc(*'H264')
        else:
            self.fourcc = cv2.VideoWriter_fourcc(*'MJPG')
        self.video_writer = None
        self.frame_count = 0
        self.direction = direction

        if filename:
            self.log_path = filename
        else:
            # DayName-Month-DayNumber-Year_Hours-Minutes-Seconds-AM/PM
            time_str = datetime.today().strftime("%a-%b-%d-%Y_%I-%M-%S-%p")
            name = '{}_{}.avi'.format(direction, time_str)
            self.log_path = os.path.join(log_base_path, name)

        frame_var_name = 'frame_num_{}'.format(self.direction)
        if not hasattr(shm.camera, frame_var_name):
            print("WARNING: no frame number variable in shm for direction {}!".format(self.direction))
            self.frame_var = None
        else:
            self.frame_var = getattr(shm.camera, frame_var_name)

    def log_image(self, mat):
        # write the current frame number to shm. this is useful for shm logging,
        #  and shm log playback
        if self.frame_var is not None:
            self.frame_var.set(self.frame_count)

        self.frame_count += 1
        if self.video_writer is None:
            self.video_writer = cv2.VideoWriter(self.log_path, self.fourcc, 10.,
                                                (mat.shape[1], mat.shape[0]))

        if mat.shape[2] == 3:
            self.video_writer.write(mat)
        elif mat.shape[2] == 1:
            mat = cv2.merge((mat, mat, mat))
            self.video_writer.write(mat)
        else:
            print(f"Invalid Image Shape for {self.direction}! ({mat.shape[2]})")

    def close(self):
        if self.video_writer is not None:
            self.video_writer.release()
            self.video_writer = None

