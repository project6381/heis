import panel_driver
from threading import Thread
from threading import Lock
import time


class Panel:
	def __init__(self):
		self.button_list = []
		self.mutex_key = Lock()
		self.thread_started = False
		self.polling_thread = Thread(target = self.polling_buttons, args = (),)

	def polling_buttons(self):
		old_button = -1
		self.thread_started = True
		while True:
			button = panel_driver.read_buttons()
			if button >= 0 and button != old_button:
				self.mutex_key.acquire()
				self.button_list.append(button)	
				self.mutex_key.release()
				print (self.button_list)
				old_button = button	

	#polling_thread = Thread(target = polling_buttons, args = (),)

	def read_pressed_button(self):
		if self.thread_started is not True:
			self.start(self.polling_thread)
		if self.button_list:
			self.mutex_key.acquire()
			first_element = self.button_list.pop(0)
			self.mutex_key.release()
			#print first_element
			return first_element
		return 'no buttons pressed'	
		
	def start(self,thread):
		thread.daemon = True # Terminate thread when "main" is finished
		thread.start()
		#thread.join()

