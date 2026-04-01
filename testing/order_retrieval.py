# order_retrieval.py

import requests
import json 
import time

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

def main():
        print("order 1:")
        name, strawberry_order, whipped_cream_order = waiting_for_order()
        print(name)
        print(f"strawberries? {strawberry_order}")
        print(f"whipped cream? {whipped_cream_order}")

        print("order 2:")
        name, strawberry_order, whipped_cream_order = waiting_for_order()
        print(name)
        print(f"strawberries? {strawberry_order}")
        print(f"whipped cream? {whipped_cream_order}")

        print("order 3:")
        name, strawberry_order, whipped_cream_order = waiting_for_order()
        print(name)
        print(f"strawberries? {strawberry_order}")
        print(f"whipped cream? {whipped_cream_order}")

        print("order 4:")
        name, strawberry_order, whipped_cream_order = waiting_for_order()
        print(name)
        print(f"strawberries? {strawberry_order}")
        print(f"whipped cream? {whipped_cream_order}")

        print("order 5:")
        name, strawberry_order, whipped_cream_order = waiting_for_order()
        print(name)
        print(f"strawberries? {strawberry_order}")
        print(f"whipped cream? {whipped_cream_order}")

if __name__ == '__main__':
    main()
        
