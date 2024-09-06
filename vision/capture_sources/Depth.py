import os
import sys
import time
import numpy as np
import cv2
import pyzed.sl as sl
import shm

from CaptureSource import CaptureSource

class Depth(CaptureSource):
    def __init__(self, direction, loop=True, shmlog=False):
        super().__init__(direction)
        self.last_time = time.time()
        self.init_params = sl.InitParameters(depth_mode=sl.DEPTH_MODE.ULTRA,
                                coordinate_units=sl.UNIT.METER,
                                coordinate_system=sl.COORDINATE_SYSTEM.RIGHT_HANDED_Y_UP,
                                depth_maximum_distance=2.0,
                                camera_resolution = sl.RESOLUTION.VGA) #Do not switch away unless usb3
        self.zed=sl.Camera()
        status = self.zed.open(self.init_params)
        
        if status != sl.ERROR_CODE.SUCCESS:
            print(repr(status))
            exit()
 

    def acquire_next_image(self):
        #zed = sl.Camera()
        #print("here")
        #status = self.zed.open(self.init_params)
        #print("got here")
        #if status != sl.ERROR_CODE.SUCCESS:
        #    print("jsdfsjkds:",repr(status))
        #    exit()
        depth_zed = sl.Mat(self.zed.get_camera_information().camera_resolution.width, self.zed.get_camera_information().camera_resolution.height, sl.MAT_TYPE.F32_C1)

        if self.zed.grab() == sl.ERROR_CODE.SUCCESS :
            self.zed.retrieve_measure(depth_zed, sl.MEASURE.DEPTH)
            depth_ocv = depth_zed.get_data()

            depth_ocv = cv2.patchNaNs(depth_ocv,2.0)
            depth_ocv[depth_ocv == float("inf")] = 2.0
            depth_ocv[depth_ocv == float("-inf")] = 2.0
            depth_ocv=depth_ocv*128
            depth_ocv=depth_ocv.astype(np.ubyte)
            

            depth_ocv2 = np.expand_dims(depth_ocv, axis=2)
            print(depth_ocv)
            #print(len(depth_ocv)/2, " ", len(depth_ocv[0])/2)
            #print(depth_ocv[int(len(depth_ocv)/2)][int(len(depth_ocv[0])/2)])
            time_to_sleep = 1 / self.fps - (time.time() - self.last_time)
            if time_to_sleep > 0:
                time.sleep(time_to_sleep)

            acq_time = time.time()
            self.last_time = acq_time
            #print(np.shape(depth_ocv2))                
            return depth_ocv2, acq_time

if __name__ == "__main__":
    if len(sys.argv) == 2:
        direction = sys.argv[1] #should be downward
        #filename = sys.argv[2]
        print("Running on %s direction." % (direction))

    else:
        print("Video needs a direction")
        sys.exit(1)

    Depth(direction).acquisition_loop()

