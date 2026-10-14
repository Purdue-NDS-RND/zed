import pyzed.sl as sl

zed = sl.Camera()

# Open using stored/factory calibration only
init = sl.InitParameters()
init.camera_disable_self_calib = True #True means it is disabled

status = zed.open(init) #This should open the camera

if status != sl.ERROR_CODE.SUCCESS:
    print("Camera open failed:", status)
    exit(1)

print("Camera opened.")

# Explicitly enable automatic exposure and gain
status = zed.set_camera_settings(
    sl.VIDEO_SETTINGS.AEC_AGC,
    1
) #This should ensure auto-exposure is enabled

print("AEC/AGC enable:", status)

# Get resolution
info = zed.get_camera_information()
res = info.camera_configuration.resolution

# Define ROI that largely excludes sky
x = int(0.10 * res.width) # % from the left
y = int(0.30 * res.height) # % from the top
w = int(0.80 * res.width) # Width of ROI
h = int(0.60 * res.height) # Height of ROI

roi = sl.Rect(x, y, w, h) #This is where we assign the ROI

status = zed.set_camera_settings_roi(
    sl.VIDEO_SETTINGS.AEC_AGC_ROI,
    roi,
    sl.SIDE.BOTH
) #This should apply the ROI

print("AEC/AGC ROI:", status)

# Let exposure converge
runtime = sl.RuntimeParameters()

successful_frames = 0

while successful_frames < 60: #This should allow the auto-exposure to hopefully work over 60 frames
    if zed.grab(runtime) == sl.ERROR_CODE.SUCCESS:
        successful_frames += 1

print("Exposure settled.")

print("Requesting self-calibration...")
zed.update_self_calibration()

# IMPORTANT:
# Stereolabs says self-calibration occurs on the
# NEXT grab() after update_self_calibration().
status = zed.grab(runtime)

if status != sl.ERROR_CODE.SUCCESS:
    print("Grab during self-calibration failed:", status)
    exit(1)

print("Self-calibration trigger frame completed.")

# Optional: grab a few additional frames afterward
for _ in range(10):
    zed.grab(runtime)

print("Test sequence complete.")

zed.close()