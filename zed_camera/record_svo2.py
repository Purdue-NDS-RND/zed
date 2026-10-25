
    
  

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
        last_encoded = 0
        last_write_progress = started
        last_write_warning = float('-inf')

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
            now = time.monotonic()
            ingested = recording.number_frames_ingested
            encoded = recording.number_frames_encoded
            details = (f'is_recording={recording.is_recording}, '
                       f'frame_status={recording.status}, '
                       f'ingested={ingested}, encoded={encoded}')
            if encoded > last_encoded:
                last_write_progress = now
                last_encoded = encoded
            # One frame-status sample is not a sustained recorder failure.
            # Encoding/writing can lag behind frame ingestion.
            if not recording.is_recording or not recording.status:
                if now - last_write_warning >= 5:
                    print(f'Recording status warning: {details}', flush=True)
                    last_write_warning = now
            if now - last_write_progress >= args.write_stall_timeout:
                raise RuntimeError(
                    f'No encoded-frame progress for {args.write_stall_timeout:g}s; '
                    f'{details}. Check free disk space, SDK logs, and output storage.')
            if now - last_report >= 5:
                print(f'Elapsed: {now - started:.1f}s; '
                      f'successful grabs: {successful_grabs}; '
                      f'warning grabs: {warning_grabs}; {details}', flush=True)
                last_report = now

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
        print('Verify the finalized frame count using ZED_SVO_Editor -inf on the output file.')
        if successful_grabs + warning_grabs == 0:
            print('No frames acquired.', file=sys.stderr)
            failed = True
    return int(failed)


if __name__ == '__main__':
    sys.exit(main())

