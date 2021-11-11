import pigpio
import signal
import requests
import logging
import json
import os
import sys
import threading
from time import sleep
from uuid import uuid1

# Global variables
BUTTON_GPIO = 23
LED_GPIO = 21
is_blinking = False
pi = pigpio.pi()
dweetFile = 'dweet_name.txt'
dweetURL = 'https://dweet.io'

# States
stateON = "ON"
stateOFF = "OFF"
stateBlink = "BLINK"
state = stateON

# Logging initialization
logging.basicConfig(level=logging.WARNING)  # Logging global configuration
logger = logging.getLogger('main') # Logger for this module
logger.setLevel(logging.INFO) # Logging configuration for this class

# next state function
def nextState():
	global state
	if state == stateON:
		state = stateOFF
		logger.info('button pressed state is changing to ' + state)
	elif state == stateOFF:
		state = stateBlink
		logger.info('button pressed state is changing to ' + state)
	elif state == stateBlink:
		state = stateON
		logger.info('button pressed state is changing to ' + state)


# Create or read dweet ID
def dweetID():
	if os.path.exists(dweetFile):
		with open(dweetFile,'r') as f:
			ID = f.read()
			logger.debug('dweet ID '+ ID)
			return ID.strip() #The strip function is used to remove spaces
	else:
		ID = str(uuid1())[:8]
		logger.debug('dweet ID ' + ID)
		with open(dweetFile,'w') as f:
			f.write(ID)
			return ID

# Sending dweet
def sendDweet(ID, stateJson):
	URL = dweetURL + '/dweet/for/' + ID
	logger.info('dweet url = ' + URL + 'json state = %s', stateJson)
	req = requests.get(URL, params=stateJson)
	
	if req.status_code == 200:
		logger.info('dweet request result = %s', req.json())
		return req.json()
	else:
		logger.error('dweet request failure : %S', req.status_code)
		return {}

# receving dweet
def getLastDweet():
	URL = dweetURL + '/get/latest/dweet/for/' + dweetID()
	logger.debug('last dweet url = ' + URL)
	req = requests.get(URL)
	if req.status_code == 200:
		dweetJson = req.json()
		logger.debug('Last dweet json = %s', dweetJson)
		dweetState = None
		if dweetJson['this'] == 'succeeded':
			dweetState = dweetJson['with'][0]['content'] 
		return dweetState
	else:
		logger.error('Last dweet error %s', req.status_code)
		return None

		
# Setting the initialization
def init():
	#Button initializtion
	pi.set_mode(BUTTON_GPIO,pigpio.INPUT)      
	pi.set_pull_up_down(BUTTON_GPIO,pigpio.PUD_UP)
	pi.set_glitch_filter(BUTTON_GPIO, 100000)  # 100000 ms = 0.1 secs
	pi.callback(BUTTON_GPIO, pigpio.FALLING_EDGE, pressed)
	#LED initialization
	pi.set_mode(LED_GPIO, pigpio.OUTPUT)
	pi.write(LED_GPIO, 1)
	#capture CTRL + C
	signal.signal(signal.SIGINT, signal_handler)

# Button handler
def pressed(gpio_pin, level, tick):
	nextState()
	logger.debug("Button pressed: state is " + state)
	sendDweet(dweetID(), {'state': state})

# Processing dweet
def processDweet( dweet):
	global state
	global is_blinking
	if not 'state' in dweet:
		return None

	dweetState = dweet['state']

	if dweetState == state:                                               
		return None  # State not changed

	is_blinking = False

	if dweetState == stateON:                                                          
		pi.write(LED_GPIO, 1)
		state = stateON
	elif dweetState == stateBlink:
		blink()
		state = stateBlink
	else:  # Turn the led off in any other case
		state = stateOFF
		pi.write(LED_GPIO, 0)

	logger.info('dweet state after receving dweet = ' + dweetState)


def print_instructions():
	print("LED Control URLs - Try them in your web browser:")
	print("  On    : " + dweetURL + "/dweet/for/" + dweetID() + "?state=ON")
	print("  Off   : " + dweetURL + "/dweet/for/" + dweetID() + "?state=OFF")
	print("  Blink : " + dweetURL + "/dweet/for/" + dweetID() + "?state=BLINK\n")


def signal_handler(sig, frame):
	print('You pressed Control+C')
	pi.write(LED_GPIO, 0)
	sys.exit(0)


def blink():
	global is_blinking

	is_blinking = True

	def do_blink():
		while is_blinking:
			pi.write(LED_GPIO, 1)
			sleep(1)
			pi.write(LED_GPIO, 0)
			sleep(1)

	# daemon=True prevents our thread below from preventing the main thread
	# (essentially the code in if __name__ == '__main__') from exiting naturally
	# when it reaches it's end. If you try daemon=False you will discover that the
	# program never quits back to the Terminal and appears to hang after the LED turns off.
	thread = threading.Thread(name='LED on GPIO ' + str(LED_GPIO), target=do_blink, daemon=True)
	thread.start()

	
# Main entry point
if __name__ == '__main__':
	init()
	print_instructions()

	print('Waiting for dweets. Press Control+C to exit.')
	while True:
		dweetState = getLastDweet()
		if dweetState is not None:
			processDweet(dweetState)
			sleep(2)






	
	
