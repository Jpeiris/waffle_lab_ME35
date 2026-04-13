# Live Figure Detection using Teachable Machine + Pi Camera
# Runs your exported Keras model against the Pi Camera feed in real time.

from keras.models import load_model
from picamera2 import Picamera2
from libcamera import controls
import cv2
import numpy as np
import time

# ── Configuration ─────────────────────────────────────────────────────────────
MODEL_PATH      = "keras_Model.h5"   # Path to your Teachable Machine model
LABELS_PATH     = "labels.txt"       # Path to your labels file
CONFIDENCE_MIN  = 0.75               # Only display prediction if confidence >= this
CAPTURE_WIDTH   = 1280                # Camera capture width
CAPTURE_HEIGHT  = 960                # Camera capture height
# ──────────────────────────────────────────────────────────────────────────────

# Disable scientific notation in numpy output
np.set_printoptions(suppress=True)

# ── Load model & labels ───────────────────────────────────────────────────────
print("Loading model...")
model = load_model(MODEL_PATH, compile=False)
class_names = open(LABELS_PATH, "r").readlines()
print(f"Model loaded. {len(class_names)} classes: {[c.strip()[2:] for c in class_names]}\n")

# ── Start Pi Camera ───────────────────────────────────────────────────────────
picam2 = Picamera2()
config = picam2.create_video_configuration(
    main={"size": (CAPTURE_WIDTH, CAPTURE_HEIGHT), "format": "RGB888"}
)
picam2.configure(config)
picam2.set_controls({"AfMode": controls.AfModeEnum.Continuous})
picam2.start()
time.sleep(2)  # Let auto-focus and exposure settle
print("Pi Camera started. Press ESC to quit.\n")

cv2.namedWindow("Live Detection", cv2.WINDOW_NORMAL)
cv2.resizeWindow("Live Detection", 1280, 960)
# ── Helper: draw a styled prediction overlay ──────────────────────────────────
def draw_overlay(frame, label, confidence, all_predictions):
    h, w = frame.shape[:2]

    # Semi-transparent top banner
    overlay = frame.copy()
    cv2.rectangle(overlay, (0, 0), (w, 70), (20, 20, 20), -1)
    cv2.addWeighted(overlay, 0.6, frame, 0.4, 0, frame)

    # Main prediction text
    bar_color = (0, 220, 100) if confidence >= CONFIDENCE_MIN else (0, 165, 255)
    cv2.putText(frame, f"{label}  {confidence*100:.1f}%",
                (12, 45), cv2.FONT_HERSHEY_DUPLEX, 1.2, (0, 0, 0), 4)
    cv2.putText(frame, f"{label}  {confidence*100:.1f}%",
                (12, 45), cv2.FONT_HERSHEY_DUPLEX, 1.2, bar_color, 2)

    # Per-class confidence bars along the bottom
    bar_h = 22
    bar_area_top = h - (len(all_predictions) * bar_h) - 10
    for i, (cname, score) in enumerate(all_predictions):
        y = bar_area_top + i * bar_h
        bar_len = int(score * (w // 2))
        bg = (30, 30, 30)
        cv2.rectangle(frame, (0, y), (w // 2, y + bar_h - 2), bg, -1)
        cv2.rectangle(frame, (0, y), (bar_len, y + bar_h - 2), bar_color, -1)
        cv2.putText(frame, f"{cname}: {score*100:.0f}%",
                    (6, y + bar_h - 6), cv2.FONT_HERSHEY_SIMPLEX, 0.5,
                    (255, 255, 255), 1)

    return frame


# ── Main loop ─────────────────────────────────────────────────────────────────
while True:
    # Capture frame from Pi Camera (returns RGB numpy array)
    frame_rgb = picam2.capture_array()

    # Convert RGB → BGR for OpenCV display
    frame_bgr = cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2BGR)

    # ── Pre-process for model (224×224, normalised to [-1, 1]) ───────────────
    model_input = cv2.resize(frame_bgr, (224, 224), interpolation=cv2.INTER_AREA)
    model_input = np.asarray(model_input, dtype=np.float32).reshape(1, 224, 224, 3)
    model_input = (model_input / 127.5) - 1

    # ── Run inference ─────────────────────────────────────────────────────────
    prediction   = model.predict(model_input, verbose=0)
    index        = np.argmax(prediction)
    confidence   = float(prediction[0][index])
    label        = class_names[index].strip()[2:]   # strip index prefix e.g. "0 "

    # Build sorted list of all class scores for the bar chart
    all_preds = sorted(
        [(class_names[i].strip()[2:], float(prediction[0][i]))
         for i in range(len(class_names))],
        key=lambda x: x[1], reverse=True
    )

    # ── Console output ────────────────────────────────────────────────────────
    print(f"Class: {label:<20} Confidence: {confidence*100:.1f}%")

    # ── Draw overlay and show ─────────────────────────────────────────────────
    display = draw_overlay(frame_bgr.copy(), label, confidence, all_preds)
    cv2.imshow("Live Detection", display)

    # ESC to quit
    if cv2.waitKey(1) & 0xFF == 27:
        print("Exiting.")
        break

# ── Cleanup ───────────────────────────────────────────────────────────────────
picam2.stop()
cv2.destroyAllWindows()
