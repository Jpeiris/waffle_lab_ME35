# camera.py
# ML for waffle pickup
#
# 1. Camera pi reads "ready" from "pickup" column in Airtable (robot is home)
#       Ex. import airtable_module as airtable
#           airtable.wait_until_ready("pickup")
# 2. Camera turns on and begins checking if waffle has been taken 
#       main ML logic 
# 3. Sends "success" to Airtable when waffle has been picked up
#       Ex. airtable.update_status("pickup", "success")
#

# the starter code below is based on p7 but idk if it actually works 😭

import airtable_module as airtable
from keras.models import load_model
from picamera2 import Picamera2
from libcamera import controls
import requests
import json 
import math

import cv2
import numpy as np
import time

# LCD SCREEN
from lcd_i2c import I2CLCD
lcd = I2CLCD(address=0x27, bus_num=1, cols=20, rows=4)

# load model
model = load_model('keras_model.h5', compile=False)
class_names = open('labels.txt').readlines()

# camera init
picam2 = Picamera2()
picam2.set_controls({'AfMode': controls.AfModeEnum.Continuous})
picam2.start()

time.sleep(2)

# --- SETTING UP AIRTABLE POLLING
BASE_ID = "appORGiY5zlUCSNcE"
UI_TABLE_ID = "tblKVh5pskWHe0XbZ"

TOKEN = "patubif58PYYOJxFO.b6bccd62347df1bc5ed36fa1d19832fdee61e296aa878ba9a6d261f21389f2db"

URL = f"https://api.airtable.com/v0/{BASE_ID}/{UI_TABLE_ID}"

Headers = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json"
}

params = {
    "sort[0][field]": "Order Number",
    "sort[0][direction]": "asc"
}

record_num = 0
total_time = 260

def get_order():
    global record_num

    r = requests.get(url=URL, headers=Headers, params=params)

    if r.status_code != 200:
        raise Exception(f"HTTP Error: {r.status_code} - {r.text}")

    data = r.json()

    if not data["records"] or record_num > len(data["records"]) - 1:
        print("no order found")
        time.sleep(.5)
        return

    record = data["records"][record_num]["fields"]

    name = record.get("Name", "")
    maple_syrup_order = record.get("Maple Syrup?", "No")
    whipped_cream_order = record.get("Whipped Cream?", "No")
    strawberry_order = record.get("Strawberries?", "No")

    record_num += 1

    return name, maple_syrup_order, whipped_cream_order, strawberry_order

def waiting_for_order():
    while True:
        order = get_order()

        if order is not None:
            return order
        
        time.sleep(0.5)

def detect_waffle():
    scores = {}

    for name in class_names:
        scores[name.strip()[2:]] = 0
                
    for _ in range(5):
        frame = picam2.capture_array()
        frame = cv2.cvtColor(frame, cv2.COLOR_RGBA2RGB)
        frame = cv2.resize(frame, (224, 224))

        image = np.asarray(frame).astype(np.float32).reshape(1, 224, 224, 3)
        image = (image / 127.5) - 1

        prediction = model.predict(image, verbose=0)

        for i, name in enumerate(class_names):
            class_name = name.strip()[2:]
            scores[class_name] += prediction[0][i]
        
    best_class = max(scores, key=scores.get)
    print(best_class)
    confidence = scores[best_class] / 5   # average over 5 frames

    if confidence < 0.1:
        return "uncertain"

    print(f"Detected {best_class}")    # waffle present or absent 

    return best_class

def wait_until_pickup():
    empty_count = 0
    print("waiting until pickup")

    while True:
        waffle_presence = detect_waffle()

        if waffle_presence == "No Waffle":
            empty_count += 1
        else:
            empty_count = 0

        if empty_count >= 2:   # plate must be empty 2 times in a row
            return True

        time.sleep(0.1)

try:
    while True:
        # poll this from the airtable
        lcd.clear()
        lcd.backlight_on()

        name, maple_syrup_order, whipped_cream_order, strawberry_order = waiting_for_order()

        name = str(name)[:20]

        order = ''
        if maple_syrup_order != 'No':
            order += 'Syrup '
        if whipped_cream_order != 'No':
            order += "'Cream "
        if strawberry_order != 'No':
            order += 'Berries '
        if whipped_cream_order == 'No' and maple_syrup_order == 'No' and strawberry_order == 'No':
            order += 'No toppings'

        order = order[:20]

        print(order)

        lcd.clear()

        lcd.write_lines([
            "PREPARING ORDER FOR ".ljust(20),
            " ".ljust(20),
            order.ljust(20),
            " ".ljust(20)
        ])

        start_col = max(0, (20 - len(name)) // 2)
        lcd.write(name, row=1, col=start_col)

        i = 1
        j = 0
        while True:
            time.sleep(1)

            if j % 5 == 0:
                progress = ("*" * i)[:20]
                lcd.write(progress.ljust(20), row=3, col=0)
                if i < 20:
                    i += 1

            status = airtable.get_status("pickup")
            if status == "ready":
                break

            j += 1
                
        lcd.clear()
        lcd.write_lines([
            "*------------------*",
            "READY FOR PICKUP!  ",
            " - RoboBriana      ",
            "*------------------*"
        ])

        print("create3 has arrived home")
        airtable.update_status("pickup", "detecting")

        print("detecting now...")
        picked_up = wait_until_pickup()
        
        if picked_up == True:
            print("about to put success")
            airtable.update_status("pickup", "success")
            time.sleep(2)
            print("waffle picked up!")

        print("resetting airtable to waiting")
        airtable.update_status("pickup", "waiting")
        time.sleep(0.1)
        lcd.clear()

except KeyboardInterrupt:
    print("\nExiting Program")
    lcd.backlight_off()
