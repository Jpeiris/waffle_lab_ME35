# waffle_lab.py

import requests
import json 
import time
import airtable_module as airtable
import line_follow_basic_AIRTABLE as create3
# import create3.py as create3

BASE_ID = "appORGiY5zlUCSNcE"
UI_TABLE_ID = "tblKVh5pskWHe0XbZ"

TOKEN = "patubif58PYYOJxFO.50831b6d04f405beb503f51241c3ce52e45f79695af3f5a8efc26540701a719a"

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
	strawberry_order = record.get("Strawberries?")
	whipped_cream_order = record.get("Whipped Cream?")

	record_num += 1
	
	return name, strawberry_order, whipped_cream_order

def waiting_for_order():
	while True:
		order = get_order()

		if order is not None: 
			return order
		
		time.sleep(0.5)

def reset_all():
	print("\nResetting Airtable to default state...\n")
	airtable.update_status("waffle", "waiting")
	airtable.update_status("strawberry", "waiting")
	airtable.update_status("whipped cream", "waiting")
	time.sleep(1)

def visit_station(station):
	print(f"Moving to {station}")
	create3.follow_line(station) #passing station into create3 file 

	print(f"Create3 arrived at {station}")
	airtable.update_status(station, "ready")
	time.sleep(2)

	print(f"Waiting for {station} completion")
	airtable.wait_until_status(station, "success")
	print(f"{station} successful!")
	time.sleep(1)

	print("Create3 moving on...")
	airtable.update_status(station, "waiting")

def go_home():
	
	#this function turns robot around, moves to starting pos, turns again

	create3.turn_around()
	create3.move_home()
	create3.turn_around()

def executing_order():
	name, strawberry_order, whipped_cream_order = waiting_for_order()

	print(name)
	print(f"strawberries? {strawberry_order}")
	print(f"whipped cream? {whipped_cream_order}")

	reset_all()

	print("Starting order...")
	
	visit_station("waffle")
	time.sleep(2)

	if whipped_cream_order == "Yes": 
		visit_station("whipped cream")
		time.sleep(2)

	if strawberry_order == "Yes":
		visit_station("strawberry")
		time.sleep(2)

	print("Going home and preparing for next order...")
	go_home()

try: 
	while True: 
		executing_order()
		time.sleep(0.01)

except KeyboardInterrupt: 
	print("\nExiting Program")
