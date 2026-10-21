import pyzed.sl as sl
import time
import signal
import sys
import cv2


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

    filename = time.strftime("recording_%Y%m%d_%H%M%S.mp4")

    camera_opened = False
    recording_started = False
    recording_finalized = False
    video = None

    frames_grabbed = 0      # real frames we got from the camera
    frames_written = 0      # frames in the MP4 (includes duplicates to fill gaps)
    consecutive_failures = 0
    error_occurred = False

    start_ts_ns = None
    wall_start = None

    try:
        # Set up camera parameters to record only video
        init_params = sl.InitParameters()
        init_params.camera_resolution = sl.RESOLUTION.HD1080
        init_params.camera_fps = 30
        init_params.depth_mode = sl.DEPTH_MODE.NONE

        status = zed.open(init_params)

        if status != sl.ERROR_CODE.SUCCESS:
            print(f"Failed to open ZED camera: {status}")
            return 1

        camera_opened = True
        print("ZED camera opened successfully!")

        cam_config = zed.get_camera_information().camera_configuration
        width = cam_config.resolution.width
        height = cam_config.resolution.height

        # Use the FPS the camera ACTUALLY opened at, not the one we asked for.
        fps = cam_config.fps
        print(f"Camera running at {width}x{height} @ {fps} FPS")

        # One Mat holding left+right side by side (no np.hstack needed).
        stereo_image = sl.Mat()

        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        video = cv2.VideoWriter(filename, fourcc, fps, (width * 2, height))

        if not video.isOpened():
            print("Failed to start MP4 recording.")
            return 1

        recording_started = True

        print("Recording started.")
        print(f"Output: {filename}")
        print("Press Ctrl+C to stop recording safely.")

        wall_start = time.monotonic()

        # Recording loop
        while not stop_requested:

            status = zed.grab()

            if status == sl.ERROR_CODE.SUCCESS:
                zed.retrieve_image(stereo_image, sl.VIEW.SIDE_BY_SIDE)

                frame = cv2.cvtColor(stereo_image.get_data(), cv2.COLOR_BGRA2BGR)

                # Use the camera's capture timestamp to decide how many frames
                # the video *should* contain by now. If the loop fell behind and
                # the camera skipped frames, repeat this frame to fill the gap so
                # playback stays at real-time speed.
                ts_ns = zed.get_timestamp(sl.TIME_REFERENCE.IMAGE).get_nanoseconds()
                if start_ts_ns is None:
                    start_ts_ns = ts_ns

                elapsed_s = (ts_ns - start_ts_ns) / 1e9
                target_frames = int(round(elapsed_s * fps)) + 1

                while frames_written < target_frames:
                    video.write(frame)
                    frames_written += 1

                frames_grabbed += 1
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
        if recording_finalized and frames_written > 0:
            print("\nRecording finished!")
            print(f"Frames grabbed from camera: {frames_grabbed}")
            print(f"Frames written to MP4:      {frames_written}")

            if wall_start is not None:
                wall_elapsed = time.monotonic() - wall_start
                if wall_elapsed > 0:
                    print(f"Effective capture rate: {frames_grabbed / wall_elapsed:.1f} FPS")

            if frames_written > frames_grabbed:
                dup = frames_written - frames_grabbed
                print(f"NOTE: {dup} frames were duplicated because the loop "
                      f"couldn't keep up with the camera.")

            print(f"Saved recording to: {filename}")

        elif recording_started:
            print("\nWARNING: Recording may be incomplete.")
            error_occurred = True

    if error_occurred or not recording_finalized:
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
