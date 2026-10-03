import pyzed.sl as sl

zed = sl.Camera()

init = sl.InitParameters()

init.set_from_svo_file("largecorrupted.svo2")

print("Attempting to open recording...")
status = zed.open(init)

print("Open status:", status)

if status == sl.ERROR_CODE.SUCCESS:
    print("Recording opened successfully")
    print("Frames:", zed.get_svo_number_of_frames())

    zed.close()
else:
    print("Failed to open recording")
    zed.close()
