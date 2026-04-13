# airtable_module.py

import airtable_module as airtable
import requests
import json 
import time

#main:
print('waiting for create3')
airtable.wait_until_ready("maple syrup")
print('create3 has arrived')
airtable.update_status("maple syrup", "executing")
print('executing now')
time.sleep(3)
airtable.update_status("maple syrup", "success")
print('success!')