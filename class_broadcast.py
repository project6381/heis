from socket import *
from threading import Thread
from threading import Lock
import time 

class Broadcast:
	def __init__(self):
		self.message_list = [] 
		self.message_list_key = Lock()
		self.thread_started = False
		self.polling = Thread(target = self.polling_messages, args = (),)


	def polling_messages(self):

		old_message = 'denne beskjeden vil aldri bli sendt'
		self.thread_started = True

		# Setup udp
		broadcast = ('', 17852)
		udp = socket(AF_INET, SOCK_DGRAM)
		udp.bind(broadcast)
		udp.setsockopt(SOL_SOCKET, SO_BROADCAST, 1)
		
		# Fetching data
		while True: 
			data, address = udp.recvfrom(1024)
			message = self.errorcheck(data)

			if message != old_message:
				self.message_list_key.acquire()
				self.message_list.append(message)
				self.message_list_key.release()
				print (self.message_list)		
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
			return 'no messeages'

	def send(self,data):
	
		send = ('<broadcast>', 17852)
		udp = socket(AF_INET, SOCK_DGRAM)
		udp.setsockopt(SOL_SOCKET, SO_BROADCAST, 1)
		message='<%s;%s>' % (str(len(data)), data)
		udp.sendto(message, send)
		#udp.close()


	def start(self,thread):
			thread.daemon = True # Terminate thread when "main" is finished
			thread.start()
			#thread.join()

	def errorcheck(self,data):
		if data[0]=='<' and data[len(data)-1]=='>':

			counter=1
			separator=False
			separator_pos=0
			for char in data:
				if char == ";" and separator==False:
					separator_pos=counter
					separator=True
				counter+=1

			message_length=str(len(data)-separator_pos-1)
			test_length=str()
			for n in range(1,separator_pos-1):
				test_length+=data[n]

			if test_length==message_length and separator==True:
				message=str()
				for n in range(separator_pos,len(data)-1):
					message+=data[n]
				return message
			else:
				return None
		else:
			return None