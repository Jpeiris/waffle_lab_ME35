import time
import json
import os
import threading

import numpy as np
import cv2
from picamera2 import Picamera2
from libcamera import controls

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
import math


# =========================
# CONFIGA
# =========================
DEBUG = True
COLORS_FILE = "colors.json"

# Camera / image
CAL_ROI_W = 100
CAL_ROI_H = 120
CAL_DELTA_H = 20
CAL_DELTA_S = 40
CAL_DELTA_V = 40
CAL_SAMPLES = 10

FOLLOW_ROI_H = 180
FOLLOW_ROI_W = 320

# Control
LINEAR_SPEED = 0.10
ANGULAR_GAIN = 0.25
ANGULAR_MAX = 1.8

# Minimum contour area to count as valid
MIN_CONTOUR_AREA = 300

# Frames without line before declaring it lost
LOST_FRAMES_THRESHOLD = 3

# =========================
# UTILS
# =========================
def dprint(*args, **kwargs):
    if DEBUG:
        print(*args, **kwargs)

def clamp(x, lo, hi):
    return max(lo, min(hi, x))

def load_colors(path=COLORS_FILE):
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}

def save_colors(colors, path=COLORS_FILE):
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(colors, f, indent=2, sort_keys=True)
    os.replace(tmp, path)

def list_colors(colors):
    names = sorted(colors.keys())
    if not names:
        print("(no saved colors yet)")
        return
    for n in names:
        print(n)

def show_color(colors, name):
    if name not in colors:
        print(f"'{name}' not found.")
        return
    entry = colors[name]
    print(f"{name}: lower={entry.get('lower')} upper={entry.get('upper')}")

def delete_color(colors, name):
    if name not in colors:
        print(f"'{name}' not found.")
        return False
    del colors[name]
    return True

def help_text():
    print(
        "\nCommands:\n"
        "  calibrate <name>   Calibrate HSV bounds for a color name\n"
        "  follow <name>      Start line following using saved bounds\n"
        "  list               List saved color names\n"
        "  show <name>        Print saved bounds\n"
        "  delete <name>      Remove a saved color\n"
        "  help               Show this help\n"
        "  quit / exit        Exit program\n"
    )


# =========================
# CAMERA SETUP
# =========================
picam2 = Picamera2()
preview_config = picam2.create_preview_configuration(
    main={"size": (640, 480), "format": "RGB888"}
)
picam2.configure(preview_config)
picam2.set_controls({"AfMode": controls.AfModeEnum.Continuous})
picam2.start()
time.sleep(1)


# =========================
# CREATE3 ROS NODE
# =========================
class Create3Driver(Node):
    def __init__(self):
        super().__init__("create3_line_follower")

        self.cmd_vel_pub = self.create_publisher(Twist, "/cmd_vel", 10)
        self.rotate_angle_client = ActionClient(self, RotateAngle, "/rotate_angle")

    def send_twist(self, linear_x=0.0, angular_z=0.0):
        msg = Twist()
        msg.linear.x = float(linear_x)
        msg.angular.z = float(angular_z)
        self.cmd_vel_pub.publish(msg)

    def stop(self):
        self.send_twist(0.0, 0.0)

    def rotate_angle(self, angle_rad, max_rotation_speed=0.5, wait=True):
        goal_msg = RotateAngle.Goal()
        goal_msg.angle = float(angle_rad)
        goal_msg.max_rotation_speed = float(max_rotation_speed)

        self.get_logger().info(
            f"Sending rotate_angle goal: angle={angle_rad:.3f} rad, "
            f"max_speed={max_rotation_speed:.3f} rad/s"
        )

        self.rotate_angle_client.wait_for_server()

        send_goal_future = self.rotate_angle_client.send_goal_async(goal_msg)
        rclpy.spin_until_future_complete(self, send_goal_future)

        goal_handle = send_goal_future.result()

        if goal_handle is None:
            self.get_logger().error("No goal handle returned.")
            return None

        if not goal_handle.accepted:
            self.get_logger().warning("rotate_angle goal was rejected.")
            return None

        self.get_logger().info("rotate_angle goal accepted.")

        if not wait:
            return goal_handle

        result_future = goal_handle.get_result_async()
        rclpy.spin_until_future_complete(self, result_future)

        result = result_future.result()
        if result is None:
            self.get_logger().error("No result returned.")
            return None

        self.get_logger().info("rotate_angle finished.")
        return result.result


robot = None


# =========================
# CALIBRATION MODE
# =========================
def _wait_for_enter(event):
    input("")
    event.set()

def calibrate_color(colors, name):
    print(f"\n[CALIBRATE] '{name}'")
    print("Place the target color in the center box.")
    print("Press Enter in the terminal to save.\n")

    enter_event = threading.Event()
    threading.Thread(target=_wait_for_enter, args=(enter_event,), daemon=True).start()

    hsv_means = []

    while True:
        image = picam2.capture_array()

        h, w = image.shape[:2]
        x0 = (w - CAL_ROI_W) // 2
        x1 = x0 + CAL_ROI_W
        y0 = (h - CAL_ROI_H) // 2
        y1 = y0 + CAL_ROI_H

        roi = image[y0:y1, x0:x1]

        blur = cv2.GaussianBlur(roi, (5, 5), 0)
        hsv = cv2.cvtColor(blur, cv2.COLOR_RGB2HSV)

        mean_hsv = np.mean(hsv, axis=(0, 1))
        hsv_means.append(mean_hsv)
        if len(hsv_means) > CAL_SAMPLES:
            hsv_means.pop(0)

        lower_tmp = np.array([
            clamp(mean_hsv[0] - CAL_DELTA_H, 0, 179),
            clamp(mean_hsv[1] - CAL_DELTA_S, 0, 255),
            clamp(mean_hsv[2] - CAL_DELTA_V, 0, 255),
        ], dtype=np.uint8)

        upper_tmp = np.array([
            clamp(mean_hsv[0] + CAL_DELTA_H, 0, 179),
            clamp(mean_hsv[1] + CAL_DELTA_S, 0, 255),
            clamp(mean_hsv[2] + CAL_DELTA_V, 0, 255),
        ], dtype=np.uint8)

        mask = cv2.inRange(hsv, lower_tmp, upper_tmp)

        display = image.copy()
        cv2.rectangle(display, (x0, y0), (x1, y1), (0, 255, 0), 2)

        cv2.imshow("calibration_frame", cv2.cvtColor(display, cv2.COLOR_RGB2BGR))
        cv2.imshow("calibration_mask", mask)
        cv2.waitKey(1)

        if enter_event.is_set():
            avg = np.mean(np.array(hsv_means), axis=0)
            H, S, V = avg.tolist()

            lower = [
                int(clamp(H - CAL_DELTA_H, 0, 179)),
                int(clamp(S - CAL_DELTA_S, 0, 255)),
                int(clamp(V - CAL_DELTA_V, 0, 255)),
            ]
            upper = [
                int(clamp(H + CAL_DELTA_H, 0, 179)),
                int(clamp(S + CAL_DELTA_S, 0, 255)),
                int(clamp(V + CAL_DELTA_V, 0, 255)),
            ]

            colors[name] = {"lower": lower, "upper": upper}
            save_colors(colors)
            print(f"Saved '{name}': lower={lower} upper={upper}\n")
            break

# =========================
# FOLLOW MODE
# Stops immediately when line disappears.
# Returns "lost" or "stopped"
# =========================

def follow_color(colors, name):
    global robot

    if name not in colors:
        print(f"'{name}' not found. Run: calibrate {name}")
        return "stopped"

    lower = np.array(colors[name]["lower"], dtype=np.uint8)
    upper = np.array(colors[name]["upper"], dtype=np.uint8)

    print(f"\n[FOLLOW] '{name}'  |  Esc or Ctrl+C to stop.\n")

    lost_frames = 0
    seen_line_once = False

    try:
        while True:
            rclpy.spin_once(robot, timeout_sec=0.0)

            image = picam2.capture_array()
            h, w = image.shape[:2]

            x0 = (w - FOLLOW_ROI_W) // 2
            x1 = x0 + FOLLOW_ROI_W
            y1 = h
            y0 = h - FOLLOW_ROI_H

            crop = image[y0:y1, x0:x1]

            blur = cv2.GaussianBlur(crop, (5, 5), 0)
            hsv = cv2.cvtColor(blur, cv2.COLOR_RGB2HSV)

            mask = cv2.inRange(hsv, lower, upper)
            mask = cv2.erode(mask, None, iterations=1)
            mask = cv2.dilate(mask, None, iterations=2)

            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            found_line = False
            cx, cy = None, None
            best_contour = None

            if contours:
                best_contour = max(contours, key=cv2.contourArea)
                area = cv2.contourArea(best_contour)
                if area > MIN_CONTOUR_AREA:
                    M = cv2.moments(best_contour)
                    if M["m00"] != 0:
                        cx = int(M["m10"] / M["m00"])
                        cy = int(M["m01"] / M["m00"])
                        found_line = True

            display = crop.copy()
            roi_center_x = crop.shape[1] // 2

            if found_line:
                seen_line_once = True
                lost_frames = 0

                error_px = cx - roi_center_x
                norm_error = error_px / (crop.shape[1] / 2.0)

                angular_z = -ANGULAR_GAIN * norm_error
                angular_z = clamp(angular_z, -ANGULAR_MAX, ANGULAR_MAX)
                linear_x = LINEAR_SPEED * (1.0 - min(abs(norm_error), 1.0) * 0.5)

                robot.send_twist(linear_x=linear_x, angular_z=angular_z)

                cv2.drawContours(display, [best_contour], -1, (0, 255, 0), 2)
                cv2.circle(display, (cx, cy), 6, (255, 0, 0), -1)

                dprint(f"TRACK  cx={cx} err={norm_error:.2f} lin={linear_x:.2f} ang={angular_z:.2f}")

            else:
                if seen_line_once:
                    lost_frames += 1
                    dprint(f"Line not seen — lost_frames={lost_frames}/{LOST_FRAMES_THRESHOLD}")
                    if lost_frames >= LOST_FRAMES_THRESHOLD:
                        robot.stop()
                        return "lost"
                else:
                    # Haven't found the line yet — creep forward slowly
                    robot.send_twist(linear_x=LINEAR_SPEED * 0.5, angular_z=0.0)
                    dprint("Waiting to acquire line...")

            cv2.line(display, (roi_center_x, 0), (roi_center_x, crop.shape[0]), (0, 0, 255), 2)
            cv2.imshow("follow_frame", cv2.cvtColor(display, cv2.COLOR_RGB2BGR))
            cv2.imshow("follow_mask", mask)

            key = cv2.waitKey(1) & 0xFF
            if key == 27:  # Esc
                robot.stop()
                return "stopped"

            time.sleep(0.03)        
    except KeyboardInterrupt:
        robot.stop()
        return "stopped"

# =========================
# COMMAND LOOP
# =========================
def command_loop():
    colors = load_colors()
    help_text()

    while True:
        try:
            cmd = input(">> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nExiting.")
            break

        if not cmd:
            continue

        parts = cmd.split()
        op = parts[0].lower()

        if op in ("quit", "exit"):
            break
        elif op == "help":
            help_text()
        elif op == "list":
            colors = load_colors()
            list_colors(colors)
        elif op == "show" and len(parts) >= 2:
            colors = load_colors()
            show_color(colors, parts[1].lower())
        elif op == "delete" and len(parts) >= 2:
            name = parts[1].lower()
            colors = load_colors()
            if delete_color(colors, name):
                save_colors(colors)
                print(f"Deleted '{name}'.")
        elif op == "calibrate" and len(parts) >= 2:
            name = parts[1].lower()
            colors = load_colors()
            calibrate_color(colors, name)
        elif op == "follow" and len(parts) >= 2:
            name = parts[1].lower()
            colors = load_colors()
            follow_color(colors, name)
        else:
            print("Unrecognized command. Type 'help'.")



# =========================
# PUBLIC API — import this
# =========================
def follow_line(color_name: str):
    """
    Follow a single colored line until it disappears, then return.
    Call this from external code (e.g. waffle_lab.py) like:
        from line_follower import follow_line
        follow_line("red")
    
    Blocks until the line is gone or Ctrl+C is pressed.
    """
    global robot

    # Initialize ROS if not already running
    if not rclpy.ok():
        rclpy.init()
    if robot is None:
        robot = Create3Driver()

    colors = load_colors()

    if color_name not in colors:
        raise ValueError(f"Color '{color_name}' not calibrated. Run the line follower CLI and use: calibrate {color_name}")

    result = follow_color(colors, color_name)
    return result  # "lost" or "stopped"


def shutdown_robot():
    """Call this when your program exits to cleanly stop the robot."""
    global robot
    if robot is not None:
        robot.stop()
        robot.destroy_node()
        robot = None
    if rclpy.ok():
        rclpy.shutdown()
    cv2.destroyAllWindows()
    picam2.stop()

# =========================
# MOVE HOME
# =========================
def move_home():
    follow_line("strawberry")
    time.sleep(0.1)
    follow_line("whipped cream")
    time.sleep(0.1)
    follow_line("waffle")
    print("home")

# =========================
# TURN AROUND
# =========================
def turn_around():
    robot.rotate_angle(math.pi)

# =========================
# MAIN
# =========================
def main():
    global robot

    rclpy.init()
    robot = Create3Driver()

    try:
        command_loop()
    finally:
        if robot is not None:
            robot.stop()
            robot.destroy_node()

        rclpy.shutdown()
        cv2.destroyAllWindows()
        picam2.stop()


if __name__ == "__main__":
    main()
