# airtable_module.py
  - module for each station to use to communicate with Airtable and the Create3

# guide for usage -- how to use this module in your code!! 

wait_until_ready(station)
- where station is "waffle", "strawberry" or "whipped cream"

update_status(station, updated_status)
- where status is either "waiting", "ready", "executing", "success" or (optionally) "failure"

# statuses: 
- "waiting"   --> default / idle state -- this will be set initially and reset by the Create3
- "ready"     --> Create3 has reached station position (station can begin executing tasks)
- "executing" --> station has begun executing tasks
- "success"   --> station has finished executing all tasks 

# sample usage: 

    import airtable_module as airtable
  
    airtable.wait_until_ready("strawberry")
    airtable.update_status("strawberry", "executing")
    cut_strawberries()    # sample function - here is where your main station code goes! 
    airtable.update_status("strawberry", "success")
