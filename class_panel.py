#import panel_driver
from threading import Thread
from threading import Lock
import time
import PanelInterface

class Panel:
	def __init__(self):
		self.button_list = []
		self.mutex_key = Lock()
		self.thread_started = False
		self.polling_thread = Thread(target = self.polling_panel, args = (),)
		self.panelInterface = PanelInterface.PanelInterface()

	def polling_panel(self):
		old_button = -1
		self.thread_started = True
		while True:
			button = self.read_panel()
			if button >= 0 and button != old_button:
				self.mutex_key.acquire()
				self.button_list.append(button)	
				self.mutex_key.release()
				print (self.button_list)
				old_button = button	
	

	def read_button(self):
		if self.thread_started is not True:
			self.start(self.polling_thread)
		if self.button_list:
			self.mutex_key.acquire()
			first_element = self.button_list.pop(0)
			self.mutex_key.release()
			#print first_element
			return first_element
		else:
			pass
			#return 'no buttons pressed'	


	def read_panel(self):

		for floor in range (0,4):
			for button in range(0,3):
				if (floor == 0 and button == 1) or (floor == 3 and button == 0):
					pass
				elif self.panelInterface.get_button_signal(button,floor):
					#print 'floor %i, button %i' % (floor, button)
					return (floor, button)

			
	def start(self,thread):
		thread.daemon = True # Terminate thread when "main" is finished
		thread.start()
		#thread.join()

