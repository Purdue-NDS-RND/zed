import pyzed.sl as sl
import cv2
import time
import signal
import sys


# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------

# Skip the on-open stereo self-calibration (the step that fails when the
# image is blown out). The factory calibration is used instead.
DISABLE_SELF_CALIBRATION = True

# Exposure, in microseconds (us). Pick ONE mode:
#
# Auto mode (MANUAL_EXPOSURE_US = None): the camera adjusts exposure itself,
# but only within the min/max range below. Lower the max if frames look
# washed out; raise it if shade looks too dark.
#
# Manual mode (MANUAL_EXPOSURE_US = a number): exposure is fixed at that value
# and never changes. Most predictable, but won't adapt to clouds or shade.
MANUAL_EXPOSURE_US = 5000
AUTO_EXPOSURE_MIN_US = 28
AUTO_EXPOSURE_MAX_US = 5000

# Which image to save:
#   sl.VIEW.LEFT          -> left camera only (normal video)
#   sl.VIEW.SIDE_BY_SIDE  -> left and right next to each other (double width)
VIEW = sl.VIEW.LEFT

# How many times to try opening the camera before giving up.
OPEN_ATTEMPTS = 3
OPEN_RETRY_DELAY_S = 3.0

MAX_CONSECUTIVE_FAILURES = 30


stop_requested = False


def request_stop(signum, frame):
    """Request a graceful shutdown without interrupting cleanup."""
    global stop_requested

    if not stop_requested:
        print("\nStop requested. Finishing recording...")

    stop_requested = True


def build_init_params():
    init = sl.InitParameters()
    init.camera_disable_self_calib = DISABLE_SELF_CALIBRATION
    # We only need images, not depth.
    init.depth_mode = sl.DEPTH_MODE.NONE
    return init


def open_camera():
    """Try to open the camera a few times. Returns an open sl.Camera or None."""
    init = build_init_params()

    for attempt in range(1, OPEN_ATTEMPTS + 1):
        if stop_requested:
            return None

        zed = sl.Camera()
        status = zed.open(init)

        if status == sl.ERROR_CODE.SUCCESS:
            return zed

        print(f"Open attempt {attempt}/{OPEN_ATTEMPTS} failed: {status}")
        zed.close()

        if attempt < OPEN_ATTEMPTS:
            time.sleep(OPEN_RETRY_DELAY_S)

    print(
        "\nCould not open the camera. If it keeps failing, the GMSL daemon "
        "may be stuck. Try:\n    sudo systemctl restart zed_x_daemon\n"
        "then run this script again."
    )
    return None


def configure_exposure(zed):
    """Apply exposure settings. Failures are warnings only."""

    if MANUAL_EXPOSURE_US is not None:
        # Manual: turn off auto exposure, then set a fixed exposure time.
        zed.set_camera_settings(sl.VIDEO_SETTINGS.AEC_AGC, 0)
        err = zed.set_camera_settings(
            sl.VIDEO_SETTINGS.EXPOSURE_TIME, MANUAL_EXPOSURE_US
        )
        if err != sl.ERROR_CODE.SUCCESS:
            print(f"Warning: could not set manual exposure: {err}")
        else:
            print(f"Manual exposure fixed at {MANUAL_EXPOSURE_US} us.")
        return

    # Auto: turn on auto exposure, then limit how long it's allowed to go.
    zed.set_camera_settings(sl.VIDEO_SETTINGS.AEC_AGC, 1)
    err = zed.set_camera_settings_range(
        sl.VIDEO_SETTINGS.AUTO_EXPOSURE_TIME_RANGE,
        AUTO_EXPOSURE_MIN_US,
        AUTO_EXPOSURE_MAX_US,
    )
    if err != sl.ERROR_CODE.SUCCESS:
        print(f"Warning: could not set auto exposure range: {err}")
    else:
        print(
            f"Auto exposure limited to "
            f"{AUTO_EXPOSURE_MIN_US}-{AUTO_EXPOSURE_MAX_US} us."
        )


def open_video_writer(base_name, width, height, fps):
    """Open an .mp4 writer; fall back to .avi (MJPG) if mp4 isn't supported."""
    for ext, codec in ((".mp4", "mp4v"), (".avi", "MJPG")):
        filename = base_name + ext
        writer = cv2.VideoWriter(
            filename, cv2.VideoWriter_fourcc(*codec), fps, (width, height)
        )
        if writer.isOpened():
            return writer, filename
        writer.release()
        print(f"Could not open {codec} writer for {filename}, trying next...")

    return None, None


def main():
    signal.signal(signal.SIGINT, request_stop)
    signal.signal(signal.SIGTERM, request_stop)

    print("Starting ZED X Mini...")

    base_name = time.strftime("recording_%Y%m%d_%H%M%S")

    zed = None
    writer = None
    filename = None

    frames_recorded = 0
    consecutive_failures = 0
    error_occurred = False

    try:
        zed = open_camera()
        if zed is None:
            return 1

        print("ZED camera opened successfully!")

        configure_exposure(zed)

        # Get frame size and frame rate from the camera.
        config = zed.get_camera_information().camera_configuration
        width = config.resolution.width
        height = config.resolution.height
        fps = config.fps

        if VIEW == sl.VIEW.SIDE_BY_SIDE:
            width *= 2

        writer, filename = open_video_writer(base_name, width, height, fps)
        if writer is None:
            print("Failed to open any video writer.")
            return 1

        print(f"Recording {width}x{height} @ {fps} fps")
        print(f"Output: {filename}")
        print("Press Ctrl+C to stop recording safely.")

        image = sl.Mat()

        while not stop_requested:
            status = zed.grab()

            if status == sl.ERROR_CODE.SUCCESS:
                consecutive_failures = 0

                # Copy the frame out of the camera (BGRA format).
                zed.retrieve_image(image, VIEW)
                # Video files need BGR (no alpha channel).
                frame = cv2.cvtColor(image.get_data(), cv2.COLOR_BGRA2BGR)

                writer.write(frame)
                frames_recorded += 1

            else:
                consecutive_failures += 1

                if consecutive_failures == 1:
                    print(f"Frame grab failed: {status}")

                if consecutive_failures >= MAX_CONSECUTIVE_FAILURES:
                    raise RuntimeError(
                        f"Camera failed {MAX_CONSECUTIVE_FAILURES} "
                        f"consecutive grabs: {status}"
                    )

                time.sleep(0.05)

    except Exception as e:
        error_occurred = True
        print(f"\nRecording error: {e}")

    finally:
        # Finish writing the video file first (this makes it playable).
        if writer is not None:
            print("\nFinalizing video file...")
            writer.release()

        if zed is not None:
            try:
                zed.close()
                print("ZED X Mini closed.")
            except Exception as e:
                error_occurred = True
                print(f"Failed to close camera: {e}")

        if frames_recorded > 0:
            print("\nRecording finished!")
            print(f"Frames recorded: {frames_recorded}")
            print(f"Saved recording to: {filename}")
        elif writer is not None:
            print("\nWARNING: No frames were recorded.")
            error_occurred = True

    if error_occurred or frames_recorded == 0:
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())