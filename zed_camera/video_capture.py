import signal
import sys
import time
import pyzed.sl as sl

# Global flag to signal the recording loop to stop
stop_signal = False


def signal_handler(signal_received, frame):
    """
    Handle interruption signals (SIGINT / SIGTERM) gracefully.
    Sets the flag so the capture loop completes the current frame cleanly,
    preventing file corruption caused by mid-frame abortion.
    """
    global stop_signal
    if not stop_signal:
        print("\n[INFO] Interrupt signal received (Ctrl+C). Stopping recording gracefully...")
        stop_signal = True
    else:
        print("\n[INFO] Shutdown already in progress. Please wait for the video to finalize...")


# Register signal handlers for both SIGINT (Ctrl+C) and SIGTERM
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)


def main():
    print("Starting ZED X Mini...")

    zed = sl.Camera()

    # Open camera with default initialization parameters
    init_params = sl.InitParameters()
    status = zed.open(init_params)

    if status != sl.ERROR_CODE.SUCCESS:
        print(f"Failed to open ZED camera: {status}")
        sys.exit(1)

    print("ZED camera opened successfully!")

    filename = time.strftime("recording_%Y%m%d_%H%M%S.svo")

    recording_params = sl.RecordingParameters(
        filename,
        sl.SVO_COMPRESSION_MODE.H264
    )

    status = zed.enable_recording(recording_params)

    if status != sl.ERROR_CODE.SUCCESS:
        print(f"Failed to start recording: {status}")
        zed.close()
        sys.exit(1)

    print(f"Recording started. Saving to: {filename}")
    print("Recording continuously. Press Ctrl+C to stop recording.")

    frames_recorded = 0
    try:
        while not stop_signal:
            if zed.grab() == sl.ERROR_CODE.SUCCESS:
                frames_recorded += 1
    except KeyboardInterrupt:
        # Fallback catch in case KeyboardInterrupt is raised
        print("\n[INFO] KeyboardInterrupt caught.")
    finally:
        # Shield finalization: Ignore subsequent SIGINT signals so repeated
        # Ctrl+C presses from impatient users do not abort the file closing.
        signal.signal(signal.SIGINT, signal.SIG_IGN)
        signal.signal(signal.SIGTERM, signal.SIG_IGN)

        print("[INFO] Finalizing and closing recording (do not interrupt)...")

        if zed.is_opened():
            # Disable recording module and flush remaining frames/metadata to disk
            zed.disable_recording()
            print("[INFO] Recording module stopped.")

            # Brief pause to allow NVENC hardware encoder and file buffers to flush
            time.sleep(0.5)

            # Safely close camera hardware
            zed.close()
            print("[INFO] ZED X Mini closed.")

        print(f"[SUCCESS] Saved recording to {filename} ({frames_recorded} frames captured).")


if __name__ == "__main__":
    main()
