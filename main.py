# Airconditioner system
#
##########################################################################################################
# Imports
import Adafruit_DHT
import RPi.GPIO as GPIO
from time import sleep
import time
import threading
import requests
import I2C_LCD_driver 
import json
import queue

from flask import Flask, render_template,request,url_for

from telegrambot import telegram_bot 

##########################################################################################################
# Set up
# Set up the DHT sensor
DHT_SENSOR = Adafruit_DHT.DHT11
DHT_PIN = 21  # GPIO pin where the DHT sensor is connected

# Set up for Keypad
LCD = I2C_LCD_driver.lcd()

# Website
app=Flask(__name__)

# Set up the GPIO for the LED
LED_PIN = 24
GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)
GPIO.setup(LED_PIN, GPIO.OUT)


BUZZER_PIN = 18
GPIO.setmode(GPIO.BCM)
GPIO.setup(BUZZER_PIN, GPIO.OUT)

##########################################################################################################
# Variables 
# Define the humidity and temperature ranges
Minimum_Humidity = 30
Maximum_Humidity= 80
Minimuim_Temperature = 18
Maximum_Temperature = 26

elapsed_time = 0
ac_on_start_time = 0
system_status = 1 
usage_status = "Ok"
##########################################################################################################
# Website
@app.route('/')
def home():
    global system_status
    system_status_str = "on" if system_status == 1 else "off"
    url = "/system_off" if system_status == 1 else "/system_on"
    return render_template('index.html', system_status=system_status_str, url=url)

@app.route('/system_off')
def system_off():
    global system_status 
    system_status = 0
    OnOff_Loop()  # Call the loop function to manage the toggle
    message = "Airconditioner Switched Off"
    telegram_bot(message)
    return render_template("system_off.html",elapsed_time=elapsed_time)

@app.route('/system_on')
def system_on():
    global system_status
    system_status = 1
    message = "Airconditioner Switched Off"
    telegram_bot(message)

###########################################################################################################
# Functions

# Function to check if air conditioner is on
def is_air_conditioner_on(humidity, temperature):
    if Minimum_Humidity <= humidity <= Maximum_Humidity and Minimuim_Temperature <= temperature <= Maximum_Temperature:
        return True
    
def exceeded_useage():
    global usage_status
    usage_status = "Exceeded"
    message = "Airconditioner Usage Exceeded! Please turn off airconditioner as soon as possible. Turn off airconditioner via this link: 127.0.0.1:5000 "
    telegram_bot(message)
    
    GPIO.output(LED_PIN,GPIO.HIGH)
    GPIO.output(BUZZER_PIN,GPIO.HIGH)
    time.sleep(0.5)
    GPIO.output(BUZZER_PIN,GPIO.LOW)
    sleep(5)

# Keypad stuff
keypad_queue = queue.Queue()

def key_pressed(key):
    keypad_queue.put(key)

def get_key():
    MATRIX=[ [1,2,3],
            [4,5,6],
            [7,8,9],
            ['*',0,'#']] #layout of keys on keypad
    ROW=[6,20,19,13] #row pins
    COL=[12,5,16] #column pins

    #set column pins as outputs, and write default value of 1 to each
    for i in range(3):
        GPIO.setup(COL[i],GPIO.OUT)
        GPIO.output(COL[i],1)

    #set row pins as inputs, with pull up
    for j in range(4):
        GPIO.setup(ROW[j],GPIO.IN,pull_up_down=GPIO.PUD_UP)

    #scan keypad
    while (True):
        for i in range(3): #loop thru’ all columns
            GPIO.output(COL[i],0) #pull one column pin low
            for j in range(4): #check which row pin becomes low
                if GPIO.input(ROW[j])==0: #if a key is pressed
                    print (MATRIX[j][i]) #print the key pressed
                    return MATRIX[j][i]
                    while GPIO.input(ROW[j])==0: #debounce
                        sleep(0.1)
            GPIO.output(COL[i],1) #write back default value of 1
            

# Keypad_Interrupt
def keypad_interupt():
    # Display initial message
    key = 0
        
    LCD.lcd_clear()
    LCD.lcd_display_string("1.Time", 1)
    LCD.lcd_display_string("2.Data", 2)
    sleep(2)
    LCD.lcd_clear()
    LCD.lcd_display_string("3.ON/OFF", 1)
    
    key = None
    while key not in [1, 2, 3]:
        key = keypad_queue.get()

    """key = get_key()
    print("value of the key is:")
    print(str(key))"""

    if key == 1:
        LCD.lcd_display_string(str(elapsed_time),1)
    elif key == 2:
        # Shows previous readings
        resp=requests.get("https://api.thingspeak.com/channels/2591947/feeds.json?api_key=XUXD1E5DUX4K5W4T&results=2")  
        print(resp.text)
        previous_readings = json.loads(resp.text) # Converts the downloaded data from the cloud from json
        # Prints into the terminal / serial monitor
        for x in range(10):
            print("Previous Reading ",x,": temperature =",previous_readings["feeds"][x]["field1"],", humidity =",previous_readings["feeds"][x]["field2"])

            string = "Temperature" + str(x)
            LCD.lcd_display_string(string,1) # Lable the reading below
            # string = str(previous_readings["feeds"][x]["field1"]) # creates string for LCD function
            LCD.lcd_display_string(str(previous_readings["feeds"][x]["field1"]),2) # LCD dislays temperature
            time.sleep(2)
            LCD.lcd_clear()

            string = "Humidity " + str(x)
            LCD.lcd_display_string(string,1) # Lable the reading below
            # string = str(previous_readings["feeds"][x]["field2"])
            LCD.lcd_display_string(str(previous_readings["feeds"][x]["field2"]),2) # LCD displays humidity
            time.sleep(2)
            LCD.lcd_clear()

    elif key == 3:  # Toggle On/Off
        global system_status
        system_status = 1 - system_status  # Toggle between 0 and 1
        OnOff_Loop()  # Call the loop function to manage the toggle
       

##########################################################################################################
# Threads
# Airconditioner_Timer_T
def airconditioner_timer():
    global elapsed_time
    global ac_on_start_time

    while system_status == 1:
        # Read humidity and temperature from the DHT sensor
        humidity, temperature = Adafruit_DHT.read(DHT_SENSOR, DHT_PIN)
        LCD.lcd_clear()
        LCD.lcd_display_string("Aircon",1)
        LCD.lcd_display_string("Timer",2)

        # Checks if the DHT Sensor Successfully reads the Humidity and the Temperature
        if humidity is not None and temperature is not None:
            #Prints out the Humidity and the Temperature inside of the terminal / Serial Monitor
            print(f"Humidity: {humidity:.2f}%, Temperature: {temperature:.2f}°C")
            print("Reading successful")
            upload_data()     

            #Calls on the function to check if the airconditioner is on
            if is_air_conditioner_on(humidity, temperature):
                #Checks that the start timer is 0
                if ac_on_start_time == 0:
                    ac_on_start_time = time.time()  # Start the timer
                    print("Timer is started")
                else:
                    elapsed_time = time.time() - ac_on_start_time
                    print(f"Air conditioner has been on for {elapsed_time:.2f} seconds")  # Prints into terminal / Serial Monitor
                    # Checks if the airconditioner has been on for more than 60 Seconds (Shortened for testing sake)

    
                    LCD.lcd_clear()
                    LCD.lcd_display_string("Elasped Time:",1)
                    LCD.lcd_display_string(str(elapsed_time),2)
                        
                    if elapsed_time > 60:   
                        GPIO.output(LED_PIN, GPIO.HIGH)  # Turn on the LED
                        print("LED ON: Air conditioner has been on for more than a minute")
                        
                        exceeded_useage()
                        keypad_interupt()
            else:
                ac_on_start_time = 0  # Reset the timer
                GPIO.output(LED_PIN, GPIO.LOW)  # Turn off the LED
                print("Aircon Not On")

        else:
            print("Failed to retrieve data from humidity sensor")
        time.sleep(5)  # Wait for 20 seconds before the next rudo eading

    elapsed_time = time.time() - ac_on_start_time
    LCD.lcd_display_string("Timer Stopped",1)
    LCD.lcd_clear()

# Upload_Data_Thread
def upload_data():
    # Upload data to thinkspeak
    humidity, temperature = Adafruit_DHT.read(DHT_SENSOR, DHT_PIN)
    resp = requests.get("https://api.thingspeak.com/update?api_key=Q5WYV1VLWZQGPWBR&field1=%s&field2=%s"%(temperature,humidity))
    # time.sleep(20) # Need to sleep for at least 20

def OnOff_Loop():
    global system_status
    if system_status == 0:
        # System is off
        LCD.lcd_clear()
        GPIO.output(BUZZER_PIN, GPIO.LOW)
        GPIO.output(LED_PIN, GPIO.LOW)
        LCD.lcd_display_string("System OFF", 1)
        print("System is turned OFF")
        LCD.lcd_display_string("1.On",2)

        key = None
        while key not in [1]:
            key = keypad_queue.get()
        if key == 1:
            system_status = 1

    if system_status == 1:
        # System is on
        airconditioner_timer_thread = threading.Thread(target=airconditioner_timer)
        airconditioner_timer_thread.start()
        print("System is turned ON")
        
                
##########################################################################################################
# Telegram Bot
# 7443228939:AAH1Yc_Zb4LpH_naJC1o2TbbKj_zCaBU-2I
# telegram_bot()
##########################################################################################################
# Main function that holds essentially all the code
def main():
    global system_status
    OnOff_Loop()
    # if system_status == 1:
        # ac_timer_thread = threading.Thread(target=airconditioner_timer)  # Thread for the airconditioner_timer function
        # ac_timer_thread.start()

    keypad_thread = threading.Thread(target=get_key)
    keypad_thread.start()
##########################################################################################################

# def start_flask_app():
#   app.run(debug=True, host='0.0.0.0', port=5002)

##########################################################################################################

# Code Starts here
if __name__ == "__main__":
    # app.run(debug=True,host='0.0.0.0', port='80')
    main_thread = threading.Thread(target=main)
    main_thread.start()
    app.run(debug=True, host='0.0.0.0', port=5002)
    # main()

