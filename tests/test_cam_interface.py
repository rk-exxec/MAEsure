import sys
from vimba import Vimba, Frame, Camera
import time

with Vimba.get_instance() as vimba:
    cams = vimba.get_all_cameras()
    cam: Camera = cams[0]
    with cam:
        # frame: Frame = cam.get_frame()
        # print(str(frame.get_timestamp()))
        # time.sleep(1)
        frame: Frame = cam.get_frame()
        print(str(frame.get_timestamp()))
        print(str(cam.AcquisitionFrameRate.get()))
    # cam_interface = vimba.interface(0)
    # cam_system = vimba.system()
    # cam_interface.open()
    # cam.open()
    # ftrs = cam.feature_names()
    # # for ftr in ftrs:
    # #     print(ftr)
    # #print(cam_interface.feature_names())
    # #print(cam_system.feature_names())
    # print('Ranges')
    # feature = cam.feature('Width')
    # feature.value = 128
    # print(feature.value)
    # print(feature.range)
    # feature = cam.feature('Height')
    # print(feature.value)
    # print(feature.range)
    # feature = cam.feature('OffsetX')
    
    # print(feature.value)
    # print(feature.range)
    # feature = cam.feature('OffsetY')
    # print(feature.value)
    # print(feature.range)
