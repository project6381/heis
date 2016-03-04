from socket import *
from threading import Thread
from threading import Lock
import time 
import broadcast 

class MessageHandler:
	def __init__(self):
		self.message_list = [] 
		self.message_list_key = Lock()
		self.thread_started = False
		self.polling = Thread(target = self.polling_messages, args = (),)


	def polling_messages(self):

		old_message = 'denne beskjeden vil aldri bli hort'
		self.thread_started = True

		# Setup udp
		port = ('', 17852)
		udp = socket(AF_INET, SOCK_DGRAM)
		udp.bind(port)
		udp.setsockopt(SOL_SOCKET, SO_BROADCAST, 1)

		
		# Fetching data
		while True:
			data, address = udp.recvfrom(1024)
			message = broadcast.errorcheck(data)
			if message != old_message:
				#with message_list_key:
				self.message_list_key.acquire()
				self.message_list.append(message)
				self.message_list_key.release()
				#print (self.message_list)		
				old_message = message
		#udp.close() 


	def read_message(self):

		# Check if thread is already running 
		if self.thread_started is not True:
			self.start(self.polling)
		if self.message_list: 
			self.message_list_key.acquire()
			first_element = self.message_list.pop(0)
			self.message_list_key.release()
			return first_element
		else:
			pass
			#return 'no messages'


	def start(self,thread):
			thread.daemon = True # Terminate thread when "main" is finished
			thread.start()
			#thread.join()

