# testing states functionality for create3 

import airtable_module as airtable
import time

def reset_all():
    print("\nResetting Airtable to default state...\n")
    airtable.update_status("waffle", "waiting")
    airtable.update_status("strawberry", "waiting")
    airtable.update_status("whipped cream", "waiting")
    time.sleep(1)

def sim_helper(station):
        print(f"Create3 arrived at {station}")
        airtable.update_status(station, "ready")
        time.sleep(2)

        airtable.wait_until_status(station, "success")
        print(f"{station} successful!")
        time.sleep(1)

        print("Create3 moving on...")
        airtable.update_status(station, "waiting")

def simulation():
        reset_all()
        
        sim_helper("waffle")
        time.sleep(2)

        sim_helper("strawberry")
        time.sleep(2)

        sim_helper("whipped cream")
        time.sleep(2)

if __name__ == "__main__":
    simulation()

# airtable.wait_until_ready("strawberry")
# airtable.update_status("strawberry", "executing")
# cut_strawberries()    # sample function - here is where your main code goes! 
# airtable.update_status("strawberry", "success")
