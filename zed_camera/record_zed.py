import pyzed.sl as sl
import time

print("Starting ZED X Mini...")

zed = sl.Camera()

status = zed.open()

if status != sl.ERROR_CODE.SUCCESS:
    print("Failed to open ZED camera.")
    exit(1)

print("ZED camera opened successfully!")

filename = time.strftime("recording_%Y%m%d_%H%M%S.svo")

recording_params = sl.RecordingParameters(
    filename,
    sl.SVO_COMPRESSION_MODE.H264
)


status = zed.enable_recording(recording_params)

if status != sl.ERROR_CODE.SUCCESS:
    print("Failed to start recording.")
    zed.close()
    exit(1)

print("Recording started.")
print("Recording continuously.")
print("Press Ctrl+C to stop recording.")

try:
    while True:
        if zed.grab() == sl.ERROR_CODE.SUCCESS:
            pass

except KeyboardInterrupt:
    print("\nStopping recording...")

finally:
    zed.disable_recording()
    print("Recording finished!")

    zed.close()
    print("ZED X Mini closed.")
    print(f"Saved recording to {filename}")

