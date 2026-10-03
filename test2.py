import pyzed.sl as sl

zed = sl.Camera()

init = sl.InitParameters()

init.set_from_svo_file("largecorrupted.svo2")

status = zed.open(init)

print("Open status:", status)

if status == sl.ERROR_CODE.SUCCESS:
    print("Recording opened successfully")
    print("Frames:", zed.get_svo_number_of_frames())

    while True:
        status = zed.grab()

        if status == sl.ERROR_CODE.SUCCESS:
            current_frame = zed.get_svo_position()

            if current_frame % 1000 == 0:
                print("Frame:", current_frame)
        elif status == sl.ERROR_CODE.END_OF_SVOFILE_REACHED:
            print("Reached end of recording")
            break

        else: 
            print("Frame error:", status)

    zed.close()
    print("Camera closed")
else:
    print("Failed to open recording")
    zed.close()
    print("Camera closed")
