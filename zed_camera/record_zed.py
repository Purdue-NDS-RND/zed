import pyzed.sl as sl
import time

print("Starting ZED X Mini...")

zed = sl.Camera()

status = zed.open()

if status != s1.ERROR_CODE.SUCCESS:
    print("Failed to opne ZED camera.")
    exit(1)

print("ZED camera opened successfully!")


recording_params = s1.RecordingParameters(
    "recording.svo",
    sl.SVO_COMPRESSION_MODE.H264
)

status = zed.enable_recording(recording_params)

if status != sl.ERROR_CODE.SUCCESS:
    print("Failed to start recording.")
    zed.close()
    exit(1)

print("Recording started")
print("Recording for 10 seconds...")

# Record for 10 seconds 
start_time = time.time()

whlie time.time() - start_time < 10:
    if zed.grab() == sl.ERROR_CODE.SUCCESS:
        pass


# Stop recording 
zed.disable_recording()

print("Recording finished!")

zed.close()

print("ZED X Mini closed.")
print("Saved recording to recording.svo")
