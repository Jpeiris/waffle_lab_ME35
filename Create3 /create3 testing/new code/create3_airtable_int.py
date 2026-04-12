# waffle_lab.py

import requests
import json 
import time
import math
import airtable_module as airtable
import line_follow_basic_AIRTABLE as create3

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

def get_order():
    global record_num

    r = requests.get(url = URL, headers = Headers, params = params)

    if r.status_code != 200:
        raise Exception(f"HTTP Error: {r.status_code} - {r.text}")

    data = r.json() 

    if not data["records"] or record_num > len(data["records"]) - 1:
        print("no order found")
        return

    record = data["records"][record_num]["fields"]

    name = record.get("Name")
    maple_syrup_order = record.get("Maple Syrup?")
    whipped_cream_order = record.get("Whipped Cream?")
    strawberry_order = record.get("Strawberries?")

    record_num += 1

    return name, maple_syrup_order, whipped_cream_order, strawberry_order

def waiting_for_order():
    while True:
        order = get_order()

        if order is not None: 
            return order
        
        time.sleep(0.5)

def reset_all():
    print("\nResetting Airtable to default state...\n")
    airtable.update_status("pickup", "waiting")
    airtable.update_status("waffle", "waiting")
    airtable.update_status("maple syrup", "waiting")
    airtable.update_status("whipped cream", "waiting")
    airtable.update_status("strawberry", "waiting")
    time.sleep(1)

def visit_station(station):
    print(f"Moving to {station}")
    create3.follow_line(station)

    print(f"Create3 arrived at {station}")
    airtable.update_status(station, "ready")
    time.sleep(2)

    print(f"Waiting for {station} completion")
    airtable.wait_until_status(station, "success")
    print(f"{station} successful!")
    time.sleep(1)

    print("Create3 moving on...")
    airtable.update_status(station, "waiting")

def executing_order():
    name, maple_syrup_order, whipped_cream_order, strawberry_order = waiting_for_order()

    print(name)
    print(f"maple syrup? {maple_syrup_order}")
    print(f"whipped cream? {whipped_cream_order}")
    print(f"strawberries? {strawberry_order}")

    reset_all()

    print("Starting order...")
    
    visit_station("waffle")
    time.sleep(2)

    if maple_syrup_order == "Yes":
        visit_station("maple syrup")
        time.sleep(2)

    if whipped_cream_order == "Yes": 
        visit_station("whipped cream")
        time.sleep(2)

    if strawberry_order == "Yes":
        visit_station("strawberry")
        time.sleep(2)

    print("Going home...")
    create3.turn(math.pi)
    time.sleep(1)
    
    if strawberry_order == "Yes":
        create3.follow_line("strawberry")
        time.sleep(1)
        create3.follow_line("whipped cream")
        time.sleep(1)
        create3.follow_line("maple syrup")

    elif whipped_cream_order == "Yes": 
        create3.follow_line("whipped cream")
        time.sleep(1)
        create3.follow_line("maple syrup")

    elif maple_syrup_order == "Yes": 
        create3.follow_line("maple syrup")
        time.sleep(1) #
	
    time.sleep(1)
    create3.follow_line("waffle")
    time.sleep(1)

    print("Waiting for customer to pickup...")
    create3.turn(math.pi / 2)
    airtable.update_status("pickup", "ready")
    time.sleep(2)

    airtable.wait_until_status("pickup", "success")
    time.sleep(2)

    print("Preparing next order...")
    create3.turn(math.pi / 2)

try: 
    while True: 
        executing_order()
        time.sleep(0.5)

except KeyboardInterrupt: 
        print("\nExiting Program")
