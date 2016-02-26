import panel
import elevator
from threading import Thread
from threading import Lock
import time

buttonList = []
mutexKey = Lock()	


def pull_buttons():
	oldButton = -1
	while True:
		button = panel.read_buttons()
		if button >= 0 and button != oldButton:
			mutexKey.acquire()
			buttonList.append(button)	
			mutexKey.release()
			print (buttonList)
			oldButton = button	

def read_pressed_buttons():

	while True:
		if buttonList:
			mutexKey.acquire()
			buttonList.pop(0)
			mutexKey.release()
			print (buttonList)
		time.sleep(5) # delays for 5 seconds
	
def thready():

	thread_1 = Thread(target = pull_buttons, args = (),)
	thread_2 = Thread(target = read_pressed_buttons, args = (),)

	thread_1.start()
	thread_2.start()

	thread_1.join()
	thread_2.join()


