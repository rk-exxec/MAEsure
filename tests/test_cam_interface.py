from pymba import Vimba, Frame

with Vimba() as vimba:
    cam = vimba.camera(0)
    cam_interface = vimba.interface(0)
    cam_system = vimba.system()
    cam_interface.open()
    cam.open()
    ftrs = cam.feature_names()
    # for ftr in ftrs:
    #     print(ftr)
    #print(cam_interface.feature_names())
    #print(cam_system.feature_names())
    print('Ranges')
    feature = cam.feature('Width')
    feature.value = 128
    print(feature.value)
    print(feature.range)
    feature = cam.feature('Height')
    print(feature.value)
    print(feature.range)
    feature = cam.feature('OffsetX')
    
    print(feature.value)
    print(feature.range)
    feature = cam.feature('OffsetY')
    print(feature.value)
    print(feature.range)
