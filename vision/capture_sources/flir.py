#!/usr/bin/env python3

import PySpin
from typing import Tuple

from vision.core.capture_source import CaptureSource, FpsLimiter

FLIR_FPS = 10
FLIR_DIRECTION = 'forward'


def flir_calibrate_udl(*_):
    pass


def flir_capture_udl(limiter: FpsLimiter, args: Tuple):
    camera = args[0]
    processor = args[1]

    for acquisition_time in limiter.rate(FLIR_FPS):
        image = None
        while image is None:
            try:
                image = camera.GetNextImage()
            except:
                pass

        image_converted = processor.Convert(image, PySpin.PixelFormat_BGR8)
        image.Release()

        image_raw = image_converted.GetData()
        image_final = image_raw.reshape((1080, 1440, 3))

        yield FLIR_DIRECTION, acquisition_time, image_final


if __name__ == '__main__':
    system = PySpin.System.GetInstance()
    cam_list = system.GetCameras()
    camera = cam_list[0]
    camera.Init()

    # self.camera.AcquisitionFrameRateEnable.SetValue(True)
    # self.camera.AcquisitionFrameRate.SetValue(self.fps)

    nodemap = camera.GetNodeMap()

    # Set the camera's acquisition mode to continuous.
    node_acquisition_mode = PySpin.CEnumerationPtr(
        nodemap.GetNode('AcquisitionMode'))
    node_acquisition_mode_continuous = node_acquisition_mode.GetEntryByName(
        'Continuous')
    acquisition_mode_continuous = node_acquisition_mode_continuous.GetValue()
    node_acquisition_mode.SetIntValue(acquisition_mode_continuous)

    # Set the camera's pixel format to RGB8.
    node_pixel_format = PySpin.CEnumerationPtr(
        nodemap.GetNode('PixelFormat'))
    node_pixel_format_rgb8 = PySpin.CEnumEntryPtr(
        node_pixel_format.GetEntryByName('BGR8'))
    pixel_format_rgb8 = node_pixel_format_rgb8.GetValue()
    node_pixel_format.SetIntValue(pixel_format_rgb8)

    camera.BeginAcquisition()

    processor = PySpin.ImageProcessor()
    processor.SetColorProcessing(
        PySpin.SPINNAKER_COLOR_PROCESSING_ALGORITHM_HQ_LINEAR)

    try:
        cs = CaptureSource()
        cs.register_capture_udl(
            FLIR_DIRECTION, flir_capture_udl, args=(camera, processor))
        cs.register_logical_udl(flir_calibrate_udl)
        cs.run_event_loop()
    except:
        pass
    finally:
        del camera
        cam_list.Clear()
        system.ReleaseInstance()
