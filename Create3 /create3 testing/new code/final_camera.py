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

import cv2
import numpy as np
import time

# load model
model = load_model('keras_model.h5', compile=False)
class_names = open('labels.txt').readlines()

# camera init
picam2 = Picamera2()
picam2.set_controls({'AfMode': controls.AfModeEnum.Continuous})
picam2.start()

time.sleep(2)

def detect_waffle():
        scores = {}

        for name in class_names:
                scores[name.strip()[2:]] = 0
                

        for _ in range(5):

                frame = picam2.capture_array()
                frame = cv2.cvtColor(frame, cv2.COLOR_RGBA2RGB)

                frame = cv2.resize(frame, (224,224))

                image = np.asarray(frame).astype(np.float32).reshape(1,224,224,3)
                image = (image / 127.5) - 1

                prediction = model.predict(image, verbose=0)

                for i,name in enumerate(class_names):
                        class_name = name.strip()[2:]
                        scores[class_name] += prediction[0][i]
        
        best_class = max(scores, key=scores.get)
        #print(best_class)
        confidence = scores[best_class] / 5  # average

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

        if empty_count >= 3:   # plate must be empty 3 times in a row
            return True

        time.sleep(0.1)

try:
    while True:
        print("waiting for create3")
        airtable.wait_until_ready("pickup")

        print("create3 has arrived home")
        airtable.update_status("pickup", "detecting")

        print("detecting now...")
        wait_until_pickup()
        
        if wait_until_pickup() == True:
            print("about to put success")
            airtable.update_status("pickup", "success")
            time.sleep(2)
            print("waffle picked up!")

        print("resetting airtable to waiting")
        airtable.update_status("pickup", "waiting")
        time.sleep(.1)

except KeyboardInterrupt: 
        print("\nExiting Program")
