import pyzed.sl as sl

zed = sl.Camera()

init_params = sl.InitParameters()

init_params.camera_resolution = sl.RESOLUTION.HD1200
init_params.camera_fps = 30
init_params.depth_mode = sl.DEPTH_MODE.NONE

status = zed.open(init_params)

print("Result:", status)

if status == sl.ERROR_CODE.SUCCESS:
    print("CAMERA OPENED")
    zed.close()

