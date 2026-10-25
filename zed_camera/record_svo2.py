#!/usr/bin/env python3
"""Record ZED X Mini stereo video without scene-dependent self-calibration.

Run with the Jetson's installed ZED SDK and matching pyzed Python environment.
Defaults: serial 55206385, SVGA, 15 FPS, lossless SVO2, no live depth.
Ctrl+C or SIGTERM finalizes the recording. Duration 0 records until stopped.
Disabling self-calibration preserves factory calibration; it cannot bypass
hardware, driver, CUDA, or missing calibration-file errors.

python record_svo2.py output-dir ~/recordings
"""

import argparse
from datetime import datetime
from pathlib import Path
import signal
import sys
import time


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--serial', type=int, default=55206385)
    parser.add_argument('--resolution', choices=['SVGA', 'HD1080', 'HD1200'],
                        default='SVGA')
    parser.add_argument('--fps', type=int, default=15)
    parser.add_argument('--duration', type=float, default=0,
                        help='Seconds after recording starts; 0 means until Ctrl+C.')
    parser.add_argument('--output-dir', type=Path, default=Path('~/recordings'))
    parser.add_argument('--enable-self-calibration', action='store_true',
                        help='Opt in to the startup adjustment; skipped by default.')
    parser.add_argument('--max-consecutive-errors', type=int, default=30)
    if (args := parser.parse_args()).duration < 0:
        parser.error('--duration must be nonnegative')
    if args.fps <= 0 or args.max_consecutive_errors <= 0:
        parser.error('--fps and --max-consecutive-errors must be positive')
    return args


def main():
    args = parse_args()
    # Import here so --help also works on machines without the camera SDK.
    import pyzed.sl as sl

    stop_requested = False

    def request_stop(signum, frame):
        nonlocal stop_requested
        stop_requested = True

    signal.signal(signal.SIGINT, request_stop)
    signal.signal(signal.SIGTERM, request_stop)

    output_dir = args.output_dir.expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    filename = output_dir / f'recording_{datetime.now():%Y%m%d_%H%M%S_%f}.svo2'
    zed = sl.Camera()
    recording_started = False
    failed = False
    successful_grabs = 0
    warning_grabs = 0
    consecutive_errors = 0

    try:
        init = sl.InitParameters()
        init.set_from_serial_number(args.serial)
        init.camera_resolution = getattr(sl.RESOLUTION, args.resolution)
        init.camera_fps = args.fps
        init.depth_mode = sl.DEPTH_MODE.NONE
        init.camera_disable_self_calib = not args.enable_self_calibration
        print(f'ZED SDK: {zed.get_sdk_version()}', flush=True)
        print(f'Opening serial {args.serial}: {args.resolution}@{args.fps}, '
              f'self-calibration={args.enable_self_calibration}, live depth=NONE',
              flush=True)
        status = zed.open(init)
        print(f'open(): {status}; is_opened(): {zed.is_opened()}', flush=True)
        if status.value > 0 or not zed.is_opened():
            raise RuntimeError(f'Camera could not open: {status}')
        if stop_requested:
            return 0

        config = zed.get_camera_information().camera_configuration
        print(f'Actual configuration: {config.resolution.width}x'
              f'{config.resolution.height} @ {config.fps} FPS', flush=True)
        params = sl.RecordingParameters(str(filename),
                                        sl.SVO_COMPRESSION_MODE.LOSSLESS)
        status = zed.enable_recording(params)
        if status != sl.ERROR_CODE.SUCCESS:
            raise RuntimeError(f'Could not start recording: {status}')
        recording_started = True
        print(f'Recording: {filename}\nPress Ctrl+C to finalize.', flush=True)
        started = time.monotonic()
        last_report = started
        last_warning = None

        while not stop_requested:
            if args.duration and time.monotonic() - started >= args.duration:
                break
            status = zed.grab()
            if status.value > 0:
                consecutive_errors += 1
                if consecutive_errors == 1:
                    print(f'grab() error: {status}', flush=True)
                if consecutive_errors >= args.max_consecutive_errors:
                    raise RuntimeError(f'{consecutive_errors} consecutive grab errors: {status}')
                time.sleep(0.05)
                continue

            consecutive_errors = 0
            if status.value < 0:
                warning_grabs += 1
                if status != last_warning:
                    print(f'grab() warning (continuing): {status}', flush=True)
                last_warning = status
            else:
                successful_grabs += 1
                last_warning = None

            recording = zed.get_recording_status()
            if not recording.is_recording or not recording.status:
                raise RuntimeError('SDK reports a recording/write failure.')
            if time.monotonic() - last_report >= 5:
                print(f'Elapsed: {time.monotonic() - started:.1f}s; '
                      f'successful grabs: {successful_grabs}; '
                      f'warning grabs: {warning_grabs}', flush=True)
                last_report = time.monotonic()

    except Exception as exc:
        failed = True
        print(f'Error: {exc}', file=sys.stderr, flush=True)
    finally:
        if recording_started:
            try:
                zed.disable_recording()
                print('SVO2 finalized.', flush=True)
            except Exception as exc:
                failed = True
                print(f'Finalization failed: {exc}', file=sys.stderr)
        try:
            zed.close()
        except Exception as exc:
            failed = True
            print(f'Camera close failed: {exc}', file=sys.stderr)

    if recording_started:
        print(f'Successful grabs: {successful_grabs}; warning grabs: {warning_grabs}')
        print(f'Output: {filename}')
        if successful_grabs + warning_grabs == 0:
            print('No frames acquired.', file=sys.stderr)
            failed = True
    return int(failed)


if __name__ == '__main__':
    sys.exit(main())
