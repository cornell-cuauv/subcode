#!/usr/bin/env python3

import time
import signal
import sys
import PySpin
import shm
from vision.capture_sources.capture_source import CaptureSource

class FlirCaptureSource(CaptureSource):
    def __init__(self, direction: str, fps: int = 10):
        super().__init__(direction, fps, persistent=True)
    
    def prepare(self):
        # Get and initialize the camera object.
        # WARNING: This will break if more than 1 FLIR camera is connected to the sub.
        self.system = PySpin.System.GetInstance()
        self.cam_list = self.system.GetCameras()
        self.camera = self.cam_list[0]
        self.camera.Init()

        # self.camera.AcquisitionFrameRateEnable.SetValue(True)
        # self.camera.AcquisitionFrameRate.SetValue(self.fps)

        nodemap = self.camera.GetNodeMap()

        # Set the camera's acquisition mode to continuous.
        node_acquisition_mode = PySpin.CEnumerationPtr(nodemap.GetNode('AcquisitionMode'))
        node_acquisition_mode_continuous = node_acquisition_mode.GetEntryByName('Continuous')
        acquisition_mode_continuous = node_acquisition_mode_continuous.GetValue()
        node_acquisition_mode.SetIntValue(acquisition_mode_continuous)

        # Set the camera's pixel format to RGB8.
        node_pixel_format = PySpin.CEnumerationPtr(nodemap.GetNode('PixelFormat'))
        node_pixel_format_rgb8 = PySpin.CEnumEntryPtr(node_pixel_format.GetEntryByName('BGR8'))
        pixel_format_rgb8 = node_pixel_format_rgb8.GetValue()
        node_pixel_format.SetIntValue(pixel_format_rgb8)

        self.camera.BeginAcquisition()

        self.processor = PySpin.ImageProcessor()
        self.processor.SetColorProcessing(PySpin.SPINNAKER_COLOR_PROCESSING_ALGORITHM_HQ_LINEAR)
    
    def _capture(self):
        image_result = None
        while image_result is None or image_result.IsIncomplete():
            try:
                image_result = self.camera.GetNextImage()
            except:
                pass
        #print("captured image")
        return image_result
    
    def _process(self, image):
        image_converted = self.processor.Convert(image, PySpin.PixelFormat_BGR8)
        image.Release()
        image_raw = image_converted.GetData()
        image_final = image_raw.reshape((540, 960, 3))
        #print("processed image")
        return image_final
    
    def _calibrate(self):
        pass
        # auto_exposure = shm.camera_calibration.flir_auto_exposure.get()
        # if self.camera.ExposureAuto.GetValue() != auto_exposure:
        #     self.camera.ExposureAuto.SetValue(auto_exposure)
    
    def acquire_next_image(self):
        original_image = self._capture()
        image = self._process(original_image)
        return image, round(time.time())
    
    # def loop(self):
    #     while True:
    #         #print("new loop")
    #         original_image = self._capture()
    #         original_time = round(time.time())
    #         image = self._process(original_image)
    #         self._send(original_time, image)
    #         self._calibrate()
    
    def cleanup(self, *args):
        # self.persistent = False
        if 'camera' in dir(self):
            del self.camera
        if self.cam_list is not None:
            self.cam_list.Clear()
        if self.system is not None:
            self.system.ReleaseInstance()
        sys.exit()

if __name__ == '__main__':
    source = FlirCaptureSource('forward')
    # signal.signal(signal.SIGTERM, source.cleanup)
    # signal.signal(signal.SIGHUP, source.cleanup)
    # signal.signal(signal.SIGINT, source.cleanup)
    try:
        source.prepare()
        source.acquisition_loop()
    except Exception as e:
        print(e)
        source.cleanup()
