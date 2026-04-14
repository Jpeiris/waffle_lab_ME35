import RPi.GPIO as GPIO
import I2C_LCD_driver
import time

mylcd = I2C_LCD_driver.lcd()

# example code 
mylcd.lcd_clear()
mylcd.lcd_display_string(param_str + ": " + str(value) + "mm", 1) # line 1
mylcd.lcd_display_string("<BACK      NEXT>", 2) # line 2 
mylcd.lcd_display_string("Shaft Cutter", 1) # line 1
mylcd.lcd_display_string("BEGIN>", 2, 10) # line 2, col 10 
