# ============================================
# Date: 15th April, 2026: I'm building on the previous day's work by adding a way to measure pixel intensity. FIXED ROI + CURRENT vs INTENSITY
# ============================================

from pypylon import pylon
from DeviceInterface import DeviceInterface
import cv2
import numpy as np
import time
import matplotlib.pyplot as plt
import os

# ==============================
# SETTINGS
# ==============================
settle_time = 2.0
SAVE_IMAGES = True

folder = "captured_images"
os.makedirs(folder, exist_ok=True)

# ==============================
# INIT CAMERA
# ==============================
camera = pylon.InstantCamera(
    pylon.TlFactory.GetInstance().CreateFirstDevice()
)
camera.Open()

camera.PixelFormat.SetValue("Mono8")

# 🔥 Auto brightness (safe start)
camera.ExposureAuto.SetValue("Continuous")
camera.GainAuto.SetValue("Continuous")

# ==============================
# INIT MAGNET
# ==============================
Mode = "Constant Current"

DeviceInterface.reset_limit_status()
DeviceInterface.config_serialport("COM3")

# ==============================
# STEP 1: CAPTURE ONCE + SELECT ROI
# ==============================
print("Capturing initial image for ROI selection...")

grab = camera.GrabOne(2000)

if not grab.GrabSucceeded():
    camera.Close()
    raise RuntimeError("Initial image capture failed")

img = grab.Array
display = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)

print("Select ROI ONCE → Press ENTER")
roi = cv2.selectROI("Select ROI", display, False, False)
cv2.destroyWindow("Select ROI")

x, y, w, h = roi

if w == 0 or h == 0:
    camera.Close()
    raise RuntimeError("Invalid ROI selected")

print(f"ROI fixed at: x={x}, y={y}, w={w}, h={h}")

# ==============================
# DATA STORAGE
# ==============================
I_data = []
Intensity_data = []

# ==============================
# LIVE PLOT
# ==============================
plt.ion()
fig, ax = plt.subplots()

# ==============================
# MAIN LOOP
# ==============================
if DeviceInterface.connect():
    DeviceInterface.electromagnet_on()

    try:
        img_count = 0

        while True:

            # --------------------------
            # INPUT CURRENT
            # --------------------------
            user_input = input("\nEnter current (A) or 'q' to quit: ")

            if user_input.lower() == 'q':
                break

            try:
                current = float(user_input)
            except:
                print("Invalid input. Try again.")
                continue

            print(f"Setting current: {current:.2f} A")
            DeviceInterface.set_field(Mode, current)

            # --------------------------
            # WAIT
            # --------------------------
            time.sleep(settle_time)

            # --------------------------
            # CAPTURE IMAGE
            # --------------------------
            grab = camera.GrabOne(2000)

            if not grab.GrabSucceeded():
                print("Image capture failed")
                continue

            img = grab.Array

            # --------------------------
            # CALCULATE INTENSITY (FIXED ROI)
            # --------------------------
            roi_img = img[y:y+h, x:x+w]
            avg_intensity = np.mean(roi_img)

            print(f"Average Intensity: {avg_intensity:.2f}")

            # --------------------------
            # STORE DATA
            # --------------------------
            I_data.append(current)
            Intensity_data.append(avg_intensity)

            # --------------------------
            # SAVE IMAGE (OPTIONAL)
            # --------------------------
            if SAVE_IMAGES:
                filename = f"{folder}/img_{img_count:03d}_{current:.2f}A.png"
                cv2.imwrite(filename, img)
                img_count += 1

            # --------------------------
            # DISPLAY ROI ON IMAGE
            # --------------------------
            display = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
            cv2.rectangle(display, (x, y), (x+w, y+h), (0,255,0), 2)

            cv2.putText(display,
                        f"{avg_intensity:.1f}",
                        (x, y-10),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.7,
                        (0,255,0),
                        2)

            cv2.imshow("Measurement", display)
            cv2.waitKey(300)

            # --------------------------
            # LIVE PLOT
            # --------------------------
            ax.clear()
            ax.plot(I_data, Intensity_data, 'bo-')
            ax.set_xlabel("Current (A)")
            ax.set_ylabel("Avg Pixel Intensity")
            ax.set_title("Current vs Intensity (Fixed ROI)")
            ax.grid(True)

            plt.pause(0.1)

    finally:
        DeviceInterface.electromagnet_off()
        DeviceInterface.clear_comports()
        camera.Close()
        cv2.destroyAllWindows()

        # --------------------------
        # FINAL PLOT
        # --------------------------
        plt.ioff()
        plt.figure(figsize=(6,4))
        plt.plot(I_data, Intensity_data, 'bo-')
        plt.xlabel("Current (A)")
        plt.ylabel("Avg Pixel Intensity")
        plt.title("Final Plot: Current vs Intensity")
        plt.grid(True)
        plt.show()

        print("\nExperiment finished safely.")

else:
    print("Device not connected")
