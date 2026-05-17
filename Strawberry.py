
import RPi.GPIO as GPIO
import time
import airtable_module as airtable

GPIO.setwarnings(False)
GPIO.setmode(GPIO.BOARD)

#pins
Knife_PINS = [23, 24, 26, 29]
Pusher_PINS = [10, 12, 7, 8]
SECOND_CONVEYOR_PINS = [18, 19, 15, 16]
LIMIT_SWITCH_1_PIN = 11
SERVO_PIN = 3

#step
STEP_SEQ = [
    [1, 0, 1, 0],
    [0, 1, 1, 0],
    [0, 1, 0, 1],
    [1, 0, 0, 1],
]

#gpio setup
for pin in Knife_PINS + Pusher_PINS + SECOND_CONVEYOR_PINS:
    GPIO.setup(pin, GPIO.OUT)
    GPIO.output(pin, 0)

# Assuming switches wired GPIO <-> 3.3V
# not pressed = LOW, pressed = HIGH
GPIO.setup(LIMIT_SWITCH_1_PIN, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)

GPIO.setup(SERVO_PIN, GPIO.OUT)
pwm = GPIO.PWM(SERVO_PIN, 50)
pwm.start(0)

# Debug
def print_switches(label=""):
    s1 = GPIO.input(LIMIT_SWITCH_1_PIN)
    print(f"{label} LIMIT1={s1}")

#servo
SERVO_DOWN = 75
SERVO_UP = 2

def SetAngle(angle, hold_time=0.35):
    duty = 2.5 + (angle / 180.0) * 10.0
    pwm.ChangeDutyCycle(duty)
    time.sleep(hold_time)      # let servo move
    pwm.ChangeDutyCycle(0)     # stop pulses to prevent jitter

#stepper
STEP_DELAY_1 = 0.0075   # knife
STEP_DELAY_2 = 0.04   # pusher
STEP_DELAY_3 = 0.03   # second conveyor

def stepper_run(pins, steps, delay, forward=True, label="stepper"):
    seq = STEP_SEQ if forward else list(reversed(STEP_SEQ))

    for i in range(steps):
        pattern = seq[i % 4]
        print(f"Step {i+1}: {pattern}")

        for pin, val in zip(pins, pattern):
            GPIO.output(pin, val)

        time.sleep(delay)

#knife
current_pos = 0
closed_pos = -760
open_pos = 0

def move_knife(target):
    global current_pos
    steps_to_move = target - current_pos

    print(f"move_knife: current={current_pos}, target={target}, delta={steps_to_move}")

    if steps_to_move != 0:
        stepper_run(
            Knife_PINS,
            abs(steps_to_move),
            STEP_DELAY_1,
            forward=(steps_to_move > 0),
            label="knife"
        )
        current_pos = target
        print(f"knife moved to {current_pos}")
        time.sleep(0.1)
    else:
        print("knife already at target")

def knife_cut_once():
    print("knife_cut_once: DOWN")
    move_knife(closed_pos)
    time.sleep(0.4)

    print("knife_cut_once: UP")
    move_knife(open_pos)
    time.sleep(0.4)

#first conveyor
def first_conveyor():
    print("=== first_conveyor start ===")
    print_switches("At start:")

    SetAngle(SERVO_DOWN)

    timeout = time.time() + 10
    loop_count = 0

    print("Starting pusher homing toward LIMIT_SWITCH_1")

    while GPIO.input(LIMIT_SWITCH_1_PIN) == GPIO.LOW:
        loop_count += 1

        if time.time() > timeout:
            raise RuntimeError("Timeout waiting for LIMIT_SWITCH_1")

        if loop_count % 20 == 1:
            print_switches(f"Homing loop {loop_count}:")

        stepper_run(Pusher_PINS, 4, STEP_DELAY_2, forward=False, label="stepper")

    print_switches("After hit:")
    print("LIMIT_SWITCH_1 activated")
    stepper_run(Pusher_PINS, 20, STEP_DELAY_2, forward=True, label="stepper")


    time.sleep(0.2)

    move_knife(closed_pos)
    time.sleep(0.5)

    print("Servo kick")
    SetAngle(SERVO_UP)
    time.sleep(0.5)
    SetAngle(SERVO_DOWN)
    time.sleep(1)
    print("Servo kicked")

    move_knife(open_pos)
    time.sleep(0.5)

    print("Servo kick")
    SetAngle(SERVO_UP)
    time.sleep(0.5)
    SetAngle(SERVO_DOWN)
    time.sleep(1)
    print("Servo kicked")

    time.sleep(0.25)
    print("=== first_conveyor end ===")

#second conveyor
CutThickness=12
NumCuts=4
StartPushSteps = 32

def second_conveyor():
    stepper_run(SECOND_CONVEYOR_PINS, StartPushSteps, STEP_DELAY_3 , forward=True, label="stepper2")

    for i in range((NumCuts-1)):
        stepper_run(SECOND_CONVEYOR_PINS, CutThickness, STEP_DELAY_3 , forward=True, label="stepper2")
        time.sleep(1)

        move_knife(closed_pos)
        time.sleep(0.5)
        move_knife(open_pos)
        time.sleep(0.5)
        print("second round")

    stepper_run(SECOND_CONVEYOR_PINS, CutThickness, STEP_DELAY_3 , forward=True, label="stepper2")
    time.sleep(1)
    stepper_run(SECOND_CONVEYOR_PINS, 80+CutThickness, STEP_DELAY_3 , forward=False, label="stepper2")

#main
try:
    print("Program start")
    print_switches("Startup:")

    #print("Setting strawberry to ready automatically...")
    #airtable.update_status("strawberry", "ready")

    while True:
        print("Waiting for strawberry ready...")
        airtable.wait_until_ready("strawberry")
        print("Strawberry request received. Starting robot...")

        airtable.update_status("strawberry", "executing")

        try:
            first_conveyor()
            print("First conveyor complete. Starting second conveyor...")

            second_conveyor()
            print("Second conveyor complete.")

            airtable.update_status("strawberry", "success")
            time.sleep(1)

            # if you want only one full cycle, break here:
            #break

        except Exception as e:
            print(f"Error during strawberry cycle: {e}")
            airtable.update_status("strawberry", "failure")
            time.sleep(1)
            break

except KeyboardInterrupt:
    print("\nKeyboard Interrupt")

finally:
    print("Cleaning up GPIO")
    pwm.stop()
    for pin in Knife_PINS + Pusher_PINS + SECOND_CONVEYOR_PINS:
        GPIO.output(pin, 0)
    GPIO.cleanup()
