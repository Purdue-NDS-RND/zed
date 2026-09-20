import pyzed.sl as sl
import time
import signal
import sys


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
        "recording_%Y%m%d_%H%M%S.svo2"
    )

    camera_opened = False
    recording_started = False
    recording_finalized = False

    frames_recorded = 0
    consecutive_failures = 0
    error_occurred = False

    try:
        # Open camera
        status = zed.open()

        if status != sl.ERROR_CODE.SUCCESS:
            print(f"Failed to open ZED camera: {status}")
            return 1

        camera_opened = True

        print("ZED camera opened successfully!")

        # Configure recording
        recording_params = sl.RecordingParameters(
            filename,
            sl.SVO_COMPRESSION_MODE.LOSSLESS
        )

        # Start recording
        status = zed.enable_recording(recording_params)

        if status != sl.ERROR_CODE.SUCCESS:
            print(f"Failed to start recording: {status}")
            return 1

        recording_started = True

        print("Recording started.")
        print(f"Output: {filename}")
        print("Press Ctrl+C to stop recording safely.")

        # Recording loop
        while not stop_requested:

            status = zed.grab()

            if status == sl.ERROR_CODE.SUCCESS:
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

        # Finalize the SVO2 before closing the camera.
        if recording_started:

            print("\nFinalizing SVO2 recording...")

            try:
                zed.disable_recording()

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
