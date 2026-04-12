import time
import classifier

# placeholder values
CHECK_INTERVAL = 1.0
EXTRA_WAIT_AFTER_REMOVED = 2.0

# adjust these if your model ends up using different class numbers
CLASS_WAFFLE_PRESENT = 0   # class 1 in Teachable Machine
CLASS_WAFFLE_REMOVED = 1   # class 2 in Teachable Machine


def main():
    # later this can be replaced with Airtable polling
    # for now, just press Enter when the robot is home
    input("Press Enter when the robot has arrived home and waffle detection should start...")

    classifier.setup()

    try:
        print("Started waffle detection.")

        while True:
            result = classifier.classify(num_images=3, show_image=False, delay=0.05)

            if result == CLASS_WAFFLE_PRESENT:
                print("Waffle detected. Waiting...")
                time.sleep(CHECK_INTERVAL)

            elif result == CLASS_WAFFLE_REMOVED:
                print("No waffle detected. Waiting 2 extra seconds...")
                time.sleep(EXTRA_WAIT_AFTER_REMOVED)
                print("finished")
                break

            else:
                print(f"Unknown class returned: {result}")
                time.sleep(CHECK_INTERVAL)

    finally:
        classifier.cleanup()


if __name__ == "__main__":
    main()
