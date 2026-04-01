# airtable_module.py
module each station uses to communicate with Airtable and the Create3

# Guide for usage -- how to use this module in your code!! 

wait_until_ready(station)
- where station is "waffle", "strawberry" or "whipped cream"

update_status(station, updated_status)
- where status is either "waiting", "ready", "executing", "success" or (optionally) "failure"

# Statuses: 
- "waiting"   --> waiting for Create3 to reach position (default / idle state)
- "ready"     --> Create3 has arrived at station position and is ready to pick up item (station can begin executing tasks)
- "executing" --> station is executing their tasks
- "success"   --> station has finished executing all tasks, ready for Create3 to move on to next station

# Airtable logic example:
1. Create3 moves to waffle station 
2. Create3 tells waffle station it has arrived (sets “ready” in waffle column)  
3. Waffle station reads ready from the Create3, executes their functions (“executes” in waffle column)  
4. Waffle station tells Create3 it was a success (“success” in waffle column)  
5. Create3 reads success from waffle station, goes to next station

# Sample usage: 

    import airtable_module as airtable 
    #make sure to download the airtable_module.py file and place it in the same folder as your station's code. 

    airtable.wait_until_ready("strawberry") #This line constantly polls the strawberry column of the airtable. It waits for "ready" thene xits                                              #the loop.
    
    airtable.update_status("strawberry", "executing") #This line updates the strawberry column to "executing". Place this before you execute                                                          #your station's code.
    
    cut_strawberries() # Sample function - here is where your main station code goes! 
    
    airtable.update_status("strawberry", "success") #This line updates the strawberry column to success, indicating that your station is                                                            #complete. 
