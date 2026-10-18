import pyzed.sl as sl
import time
import signal
import sys
import cv2
import numpy as np


stop_requested = False


def request_stop(signum, frame):
    """Request a graceful shutdown without interrupting cleanup."""
    global stop_requested

    if not stop_requested:
        print("\nStop requested. Finishing recording...")

    stop_requested = True


def main():
    global stop_requested

    # Handle Ctrl+C and normal process termination.
    signal.signal(signal.SIGINT, request_stop)
    signal.signal(signal.SIGTERM, request_stop)

    print("Starting ZED X Mini...")

    zed = sl.Camera()

    filename = time.strftime(
        "recording_%Y%m%d_%H%M%S.mp4"
    )

    camera_opened = False
    recording_started = False
    recording_finalized = False
    video = None

    frames_recorded = 0
    consecutive_failures = 0
    error_occurred = False

    try:
        # Set up camera parameters to record only video
        init_params = sl.InitParameters()
        init_params.camera_resolution = sl.RESOLUTION.HD1080
        init_params.camera_fps = 30
        init_params.depth_mode = sl.DEPTH_MODE.NONE
        # Open camera with params

        status = zed.open(init_params)

        if status != sl.ERROR_CODE.SUCCESS:
            print(f"Failed to open ZED camera: {status}")
            return 1

        camera_opened = True

        print("ZED camera opened successfully!")

        # Configure MP4 recording
        left_image = sl.Mat()
        right_image = sl.Mat()

        resolution = zed.get_camera_information().camera_configuration.resolution

        width = resolution.width
        height = resolution.height

        fourcc = cv2.VideoWriter_fourcc(*"mp4v")

        video = cv2.VideoWriter(
            filename,
            fourcc,
            30,
            (width * 2, height)
        )

        if not video.isOpened():
            print("Failed to start MP4 recording.")
            return 1

        recording_started = True

        print("Recording started.")
        print(f"Output: {filename}")
        print("Press Ctrl+C to stop recording safely.")

        # Recording loop
        while not stop_requested:

            status = zed.grab()

            if status == sl.ERROR_CODE.SUCCESS:
                zed.retrieve_image(left_image, sl.VIEW.LEFT)
                zed.retrieve_image(right_image, sl.VIEW.RIGHT)

                left_frame = cv2.cvtColor(
                    left_image.get_data(),
                    cv2.COLOR_BGRA2BGR
                )

                right_frame = cv2.cvtColor(
                    right_image.get_data(),
                    cv2.COLOR_BGRA2BGR
                )

                stereo_frame = np.hstack((left_frame, right_frame))

                video.write(stereo_frame)

                frames_recorded += 1
                consecutive_failures = 0

            else:
                consecutive_failures += 1

                if consecutive_failures == 1:
                    print(f"Frame grab failed: {status}")

                # Don't record indefinitely if the camera fails.
                if consecutive_failures >= 30:
                    raise RuntimeError(
                        f"Camera failed 30 consecutive grabs: {status}"
                    )

                time.sleep(0.05)

    except KeyboardInterrupt:
        # Fallback for a KeyboardInterrupt raised elsewhere.
        print("\nKeyboard interrupt received.")

    except Exception as e:
        error_occurred = True
        print(f"\nRecording error: {e}")

    finally:

        # Finalize the MP4 before closing the camera.
        if video is not None:

            print("\nFinalizing MP4 recording...")

            try:
                video.release()

                recording_finalized = True

                print("Recording finalized successfully!")

            except Exception as e:
                error_occurred = True

                print(f"Failed to finalize recording: {e}")

        # Always close the camera.
        if camera_opened:

            try:
                zed.close()

                print("ZED X Mini closed.")

            except Exception as e:
                error_occurred = True

                print(f"Failed to close camera: {e}")

        # Report the result.
        if recording_finalized and frames_recorded > 0:

            print("\nRecording finished!")
            print(f"Frames recorded: {frames_recorded}")
            print(f"Saved recording to: {filename}")

        elif recording_started:

            print("\nWARNING: Recording may be incomplete.")
            error_occurred = True

    if error_occurred or not recording_finalized:
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
