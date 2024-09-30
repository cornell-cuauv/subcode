#!/usr/bin/env python3

import os
import shm
import time
import numpy as np
import cv2
import pyzed.sl as sl
from vision.capture_sources.CaptureSource import CaptureSource

VIDEO_SETTINGS = sl.VIDEO_SETTINGS

class Zed(CaptureSource):
    def __init__(self, image_direction: str, depth_direction: str, normal_direction: str,
                 use_left_camera: bool = True, max_distance: float = 3, fps: int = 10):

        super().__init__('dummy', persistent=False)
        config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'vision/configs/zed.conf')
        self._init_params = sl.InitParameters(depth_mode=sl.DEPTH_MODE.NEURAL,
                                              optional_settings_path=config_path,
                                              coordinate_units=sl.UNIT.METER,
                                              coordinate_system=sl.COORDINATE_SYSTEM.RIGHT_HANDED_Y_UP,
                                              depth_maximum_distance=max_distance,
                                              camera_resolution=sl.RESOLUTION.HD720)
        self._zed = sl.Camera()
        self._direction = sl.VIEW.LEFT if use_left_camera else sl.VIEW.RIGHT
        self._image_direction = image_direction
        self._depth_direction = depth_direction
        self._normal_direction = normal_direction
        self._tick_time = 1/fps
        self._max_distance = max_distance

        self._image = sl.Mat()
        self._depth_mat = sl.Mat()
        self._normal_mat = sl.Mat()
        
        self._initialize()
        print('initialized')

    def _initialize(self):
        status = self._zed.open(self._init_params)
        if status != sl.ERROR_CODE.SUCCESS:
            print(repr(status))
            exit()

    def loop(self):
        last_time = time.time()
        print('ZED Camera initialized. Starting frame capture...')
        while True:
            self._tick()

            # apply camera calibration
            calibration = shm.camera_calibration.get()
            # if True:
            if True:
                self._zed.set_camera_settings(VIDEO_SETTINGS.BRIGHTNESS, calibration.zed_brightness)
                self._zed.set_camera_settings(VIDEO_SETTINGS.CONTRAST, calibration.zed_contrast)
                self._zed.set_camera_settings(VIDEO_SETTINGS.HUE, calibration.zed_hue)
                self._zed.set_camera_settings(VIDEO_SETTINGS.SATURATION, calibration.zed_saturation)
                self._zed.set_camera_settings(VIDEO_SETTINGS.GAMMA, calibration.zed_gamma)
                self._zed.set_camera_settings(VIDEO_SETTINGS.SHARPNESS, calibration.zed_sharpness)
                self._zed.set_camera_settings(VIDEO_SETTINGS.WHITEBALANCE_TEMPERATURE, calibration.zed_white_balance)
                self._zed.set_camera_settings(VIDEO_SETTINGS.EXPOSURE, calibration.zed_exposure)
                self._zed.set_camera_settings(VIDEO_SETTINGS.GAIN, calibration.zed_gain)
                self._zed.set_camera_settings(VIDEO_SETTINGS.AEC_AGC, 0)
                self._zed.set_camera_settings(VIDEO_SETTINGS.WHITEBALANCE_AUTO, 0)
            else:
                self._zed.set_camera_settings(VIDEO_SETTINGS.AEC_AGC, 1)
                self._zed.set_camera_settings(VIDEO_SETTINGS.WHITEBALANCE_AUTO, 1)
            # fps logic
            delta_time = time.time() - last_time
            sleep_time = self._tick_time - delta_time
            # wait
            if sleep_time > 0:
                time.sleep(sleep_time)
            last_time = time.time()

    def normal_conversion(self, normal_map):
        """
        Encodes the normal map into comatible data type for the CMF. Values
        have been changed to scale for RGB visualization
        """
        # Rescale normal vector components to be between 0 and 1
        normal_map = normal_map[..., :3]  # Remove the alpha channel (assumed to be 0)
        normal_map = (normal_map + 1) / 2.0  # Range from [-1, 1] to [0, 1]

        # Encode normal directions into RGB channels
        b = normal_map[..., 2]  # Z direction goes to blue channel
        g = normal_map[..., 1]  # Y direction goes to green channel
        r = normal_map[..., 0]  # X direction goes to red channel

        # Combine channels into a 3-channel image
        rgb_image = np.stack((r, g, b), axis=-1)

        # Convert the image to uint8 format (0-255) for OpenCV compatibility
        rgb_image = np.nan_to_num(rgb_image, nan=0.0)
        rgb_image = np.clip(rgb_image * 255.0, 0.0, 255.0).astype(np.uint8)

        return rgb_image

    def rgb_conversion(self, color_image):
        """
        Encodes the color_image to form suitable for the CMF. No
        changes in values need to be made.
        """
        return cv2.cvtColor(color_image, cv2.COLOR_RGBA2RGB)

    def depth_conversion(self, depth_ocv):
        """
        Encodes the depth map into compatible data type for CMF.
        """
        depth_ocv = cv2.patchNaNs(depth_ocv, self._max_distance)
        depth_ocv[depth_ocv == float("inf")] = self._max_distance
        depth_ocv[depth_ocv == float("-inf")] = self._max_distance
        # depth_ocv must be max 256 ie: max depth(8) * 32 = 256. scale 32 accordingly
        depth_ocv = depth_ocv*32
        depth_ocv = depth_ocv.astype(np.ubyte)
        depth_ocv2 = np.expand_dims(depth_ocv, axis=2)
        return depth_ocv2

    def _tick(self):
        if self._zed.grab() == sl.ERROR_CODE.SUCCESS:

            # Image retrieval: RGB/color, depth, and normal
            self._zed.retrieve_image(self._image, self._direction)

            image_acquisition_time = int(time.time() * 1000)
            color_image = self._image.get_data()

            self._zed.retrieve_measure(self._depth_mat, sl.MEASURE.DEPTH)
            depth_acquisition_time = int(time.time() * 1000)
            depth_ocv = self._depth_mat.get_data()

            self._zed.retrieve_measure(self._normal_mat, sl.MEASURE.NORMALS)
            normal_acquisition_time = int(time.time() * 1000)
            normal_map = self._normal_mat.get_data()

            # Processing
            normal_map = self.normal_conversion(normal_map)
            depth_map = self.depth_conversion(depth_ocv)
            rgb_image = self.rgb_conversion(color_image)
            
            # Sending the three images to the CMF.
            self._send(image_acquisition_time,
                       rgb_image, self._image_direction)
            self._send(depth_acquisition_time,
                       depth_map, self._depth_direction)
            self._send(normal_acquisition_time,
                       normal_map, self._normal_direction)


if __name__ == "__main__":
    Zed('forward', 'depth', 'normal').loop()
