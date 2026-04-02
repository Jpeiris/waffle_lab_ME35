# airtable_module.py

import airtable_module as airtable
import requests
import json 
import time

#main:
print('waiting for create3')
airtable.wait_until_ready("whipped cream")
print('create3 has arrived')
airtable.update_status("whipped cream", "executing")
print('executing now')
time.sleep(3)
airtable.update_status("whipped cream", "success")
print('success!')