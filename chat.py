import pyzed.sl as sl

print("SDK version:", sl.Camera.get_sdk_version())

zed = sl.Camera()

print("Opening camera...")

status = zed.open()

print("Open status:", status)
print("Status code:", status.value)

if status == sl.ERROR_CODE.SUCCESS:
    print("Camera opened successfully!")
    zed.close()
else:
    print("Camera failed to open.")

