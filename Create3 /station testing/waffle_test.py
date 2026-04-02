# airtable_module.py

import airtable_module as airtable
import requests
import json 
import time

#main:
print('waiting for create3')
airtable.wait_until_ready("waffle")
print('create3 has arrived')
airtable.update_status("waffle", "executing")
print('executing now')
time.sleep(3)
airtable.update_status("waffle", "success")
print('success!')