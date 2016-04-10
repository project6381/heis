from socket import *
from threading import Thread, Lock
import time
from ported_driver.constants import N_FLOORS
from config_parameters import MASTER_TO_SLAVE_PORT, SLAVE_TO_MASTER_PORT, N_ELEVATORS, MY_ID
import watchdogs
from thread import interrupt_main

class MessageHandler:

	def __init__(self):
		self.__receive_buffer_slave = [] 
		self.__receive_buffer_master = [] 	
		self.__receive_buffer_slave_key = Lock()
		self.__receive_buffer_master_key = Lock()
		self.__master_thread_started = False
		self.__slave_thread_started = False
		
		self.__slave_message = {'slave_floor_up': [0]*4,
								'slave_floor_down': [0]*4,
								'slave_id': 0,
								'last_floor': 0,
								'next_floor': 0,
								'direction': 0,
								'orders_id': 0}

		self.__master_message = {'orders_up': [0]*4,
								'orders_down': [0]*4,
								'master_id': 0,
								'orders_id': 0}

		self.__thread_buffering_master = Thread(target = self.__buffering_master_messages, args = (), name = "Buffering master thread")
		self.__thread_buffering_slave = Thread(target = self.__buffering_slave_messages, args = (),name = "Buffering slave thread")
	

	def send_to_master(self,slave_floor_up,slave_floor_down,slave_id,last_floor,next_floor,direction,orders_id):
		
		#with watchdogs.WatchdogTimer(1):
			floor_up = str()
			floor_down = str()

			for floor in slave_floor_up:
				floor_up += str(floor)	

			for floor in slave_floor_down:
				floor_down += str(floor)	


			message = "%s%s%i%i%i%i%i" % (floor_up,floor_down,slave_id,last_floor,next_floor,direction,orders_id)
			self.__send(message,SLAVE_TO_MASTER_PORT)

			print "send_to_master"
			print time.time()

			time.sleep(0.001)


	def send_to_slave(self,orders_up,orders_down,master_id,orders_id):
		#with watchdogs.WatchdogTimer(1):
			message = str()

			master_id = str(master_id)
			orders_id = str(orders_id)
			
			for order in orders_up:
				message += str(order)

			for order in orders_down:
				message += str(order)	

			message += master_id
			message += orders_id
			
			self.__send(message,MASTER_TO_SLAVE_PORT)

			print "send_to_slave"
			


	def receive_from_master(self):
		#with watchdogs.WatchdogTimer(1):
			message = self.__read_message(MASTER_TO_SLAVE_PORT)

			if message is not None:

				for i in range (0,N_FLOORS):
					self.__master_message['orders_up'][i] = int(message[i])

				for i in range (0,N_FLOORS):
					self.__master_message['orders_down'][i] = int(message[4+i])

				self.__master_message['master_id'] = int(message[8])
				self.__master_message['orders_id'] = int(message[9:])

				print "receive_from_master"

				return self.__master_message


	def receive_from_slave(self):				
		#with watchdogs.WatchdogTimer(1):
			message = self.__read_message(SLAVE_TO_MASTER_PORT)
			
			if message is not None:

				for i in range (0,4):
						self.__slave_message['slave_floor_up'][i] = int(message[i])
						self.__slave_message['slave_floor_down'][i] = int(message[4+i]) 	

				self.__slave_message['slave_id'] = int(message[8])
				self.__slave_message['last_floor'] = int(message[9])
				self.__slave_message['next_floor'] = int(message[10])
				self.__slave_message['direction'] = int(message[11])
				self.__slave_message['orders_id'] = int(message[12:])

				print "receive_from_slave"
				print time.time()

				return self.__slave_message


	def __send(self, data, port):
		#with watchdogs.WatchdogTimer(1):
			send = ('<broadcast>', port)
			udp = socket(AF_INET, SOCK_DGRAM)
			udp.setsockopt(SOL_SOCKET, SO_BROADCAST, 1)
			message='<%s;%s>' % (str(len(data)), data)
			udp.sendto(message, send)
			udp.close()



	def __read_message(self,port):
		#with watchdogs.WatchdogTimer(1):
			# Check if buffering messages threads is already running 
			if port == MASTER_TO_SLAVE_PORT:
				if self.__slave_thread_started is not True:
					self.__start(self.__thread_buffering_slave)
				
				if self.__receive_buffer_slave: 
					with self.__receive_buffer_slave_key:
						return self.__receive_buffer_slave.pop(0)
				else:
					return None

			if port == SLAVE_TO_MASTER_PORT: 
				if self.__master_thread_started is not True:
					self.__start(self.__thread_buffering_master)
				
				if self.__receive_buffer_master: 
					with self.__receive_buffer_master_key:
						return self.__receive_buffer_master.pop(0)
				else:
					return None


	def __start(self,thread):
		#with watchdogs.WatchdogTimer(1):
			thread.daemon = True # Terminate thread when "main" is finished
			thread.start()

	def __buffering_master_messages(self):
		#try:
			#__buffering_master_messages_watchdog = watchdogs.ThreadWatchdog(1,"watchdog event: MessageHandler.__buffering_master_messages_watchdog")
			#__buffering_master_messages_watchdog.StartWatchdog()

			last_message = 'This message will never be heard'
			self.__master_thread_started = True

			port = ('', SLAVE_TO_MASTER_PORT)
			udp = socket(AF_INET, SOCK_DGRAM)
			udp.bind(port)
			udp.setsockopt(SOL_SOCKET, SO_BROADCAST, 1)

			downtime = time.time() + 0.5

			while True:
				#__buffering_master_messages_watchdog.PetWatchdog()

				data, address = udp.recvfrom(1024)
				message = self.__errorcheck(data)

				if (message != last_message) or (downtime < time.time()):
					if message is not None:
						with self.__receive_buffer_master_key:
							self.__receive_buffer_master.append(message)	
					last_message = message
					downtime = time.time() + 0.5


		#except StandardError as error:
		#	print error
		#	print "MessageHandler.__buffering_master_messages"
		#	interrupt_main()


	def __buffering_slave_messages(self):
		#try:
			#__buffering_slave_messages_watchdog = watchdogs.ThreadWatchdog(1,"watchdog event: MessageHandler.__buffering_slave_messages_watchdog")
			#__buffering_slave_messages_watchdog.StartWatchdog()

			last_message = 'This message will never be heard'
			self.__slave_thread_started = True

			port = ('', MASTER_TO_SLAVE_PORT)
			udp = socket(AF_INET, SOCK_DGRAM)
			udp.bind(port)
			udp.setsockopt(SOL_SOCKET, SO_BROADCAST, 1)
			
			downtime = time.time() + 0.5

			while True:
				#__buffering_slave_messages_watchdog.PetWatchdog()
				data, address = udp.recvfrom(1024)
				message = self.__errorcheck(data)
				if (message != last_message) or (downtime < time.time()):
					if message is not None:
						with self.__receive_buffer_slave_key:
							self.__receive_buffer_slave.append(message)		
					last_message = message
					downtime = time.time() + 0.5

		#except StandardError as error:
		#	print error
		#	print "MessageHandler.__buffering_slave_messages"
		#	interrupt_main()

	def __errorcheck(self,data):
		#with watchdogs.WatchdogTimer(1):
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
