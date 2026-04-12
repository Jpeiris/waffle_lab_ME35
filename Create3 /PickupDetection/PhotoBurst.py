from picamera2 import Picamera2
from libcamera import controls
import cv2
import os
import time
import threading

# how many photos per burst
n = 10

# delay between photos in a burst
burst_delay = 0.15

folder1 = "class1photos"
folder2 = "class2photos"

os.makedirs(folder1, exist_ok=True)
os.makedirs(folder2, exist_ok=True)

picam2 = Picamera2()
picam2.set_controls({"AfMode": controls.AfModeEnum.Continuous})
picam2.start()
time.sleep(1)

current_folder = folder1
running = True
latest_frame = None
frame_lock = threading.Lock()


def next_filename(folder):
    existing = [f for f in os.listdir(folder) if f.lower().endswith(".jpg")]
    return len(existing)


def preview_loop():
    global latest_frame, running

    while running:
        frame = picam2.capture_array()

        with frame_lock:
            latest_frame = frame.copy()

        display = frame.copy()
        cv2.putText(display, f"Saving to: {current_folder}", (20, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
        cv2.putText(display, "Terminal: Enter=burst, next=switch, quit=stop", (20, 60),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

        cv2.imshow("Live Preview", display)

        # lets the window update
        if cv2.waitKey(1) & 0xFF == ord('q'):
            running = False
            break


preview_thread = threading.Thread(target=preview_loop, daemon=True)
preview_thread.start()

try:
    print("Camera ready.")
    print("Live preview opened.")
    print("Press Enter to take a burst.")
    print("Type 'next' to switch to class2photos.")
    print("Type 'quit' to stop.")
    print("You can also press 'q' in the preview window to stop.")

    while running:
        cmd = input(f"\nCurrently saving to: {current_folder}\n").strip().lower()

        if cmd == "quit":
            running = False
            break

        elif cmd == "next":
            current_folder = folder2
            print("Switched to class2photos.")

        elif cmd == "":
            start_num = next_filename(current_folder)

            for i in range(n):
                with frame_lock:
                    if latest_frame is not None:
                        frame_to_save = latest_frame.copy()
                    else:
                        frame_to_save = picam2.capture_array()

                filename = os.path.join(current_folder, f"img_{start_num + i:04d}.jpg")
                cv2.imwrite(filename, frame_to_save)
                print(f"Saved: {filename}")
                time.sleep(burst_delay)

        else:
            print("Press Enter for photos, type 'next' to switch classes, or 'quit' to stop.")

finally:
    running = False
    preview_thread.join(timeout=1)
    picam2.stop()
    cv2.destroyAllWindows()
