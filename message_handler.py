import time

from socket import socket, AF_INET, SOCK_DGRAM, SOL_SOCKET, SO_BROADCAST
from threading import Thread, Lock
from thread import interrupt_main

import watchdogs

from ported_driver.constants import N_FLOORS
from config_parameters import MASTER_TO_SLAVE_PORT, SLAVE_TO_MASTER_PORT, TICK, MASTER_TIMEOUT


class MessageHandler:
	def __init__(self):
		self.__slave_message = {'buttons_up': [0 for floor in range(0,N_FLOORS)],
								'buttons_down': [0 for floor in range(0,N_FLOORS)],
								'slave_id': 0,
								'last_floor': 0,
								'next_floor': 0,
								'direction': 0}

		self.__master_message = {'orders_up': [0 for floor in range(0,N_FLOORS)],
								'orders_down': [0 for floor in range(0,N_FLOORS)],
								'master_id': 0}

		self.__receive_buffer_slave = [] 
		self.__receive_buffer_master = [] 	
		
		self.__receive_buffer_slave_key = Lock()
		self.__receive_buffer_master_key = Lock()
		self.__is_connected_to_network_key = Lock()
		self.__no_active_master_key = Lock()

		self.__no_active_master = False
		self.__buffering_master_messages_thread_started = False
		self.__buffering_slave_messages_thread_started = False
		self.__master_alive_thread_started = False
		self.__is_connected_to_network = False

		self.__thread_buffering_master_messages = Thread(target = self.__buffering_master_messages_thread, args = (), name = "MessageHandler.__buffering_master_messages_thread")
		self.__thread_buffering_slave_messages = Thread(target = self.__buffering_slave_messages_thread, args = (),name = "MessageHandler.__buffering_slave_messages_thread")
		self.__thread_master_alive = Thread(target = self.__master_alive_thread, args = (),name = "MessageHandler.__master_alive_thread")

		self.__timeout_no_active_master = time.time() + MASTER_TIMEOUT

	def no_active_master(self):
		if self.__master_alive_thread_started is not True:
			self.__start_thread(self.__thread_master_alive)

		with self.__no_active_master_key: 
			return self.__no_active_master

	def connected_to_network(self):
		with self.__is_connected_to_network_key:
			return self.__is_connected_to_network

	def send_to_master(self,buttons_up,buttons_down,slave_id,last_floor,next_floor,direction):
		message = str()

		for button in buttons_up:
			message += str(button)	

		for button in buttons_down:
			message += str(button)

		message += str(slave_id)
		message += str(last_floor)
		message += str(next_floor)
		message += str(direction)

		self.__send(message,SLAVE_TO_MASTER_PORT)

	def send_to_slave(self,orders_up,orders_down,master_id):
		message = str()
		
		for order in orders_up:
			message += str(order)

		for order in orders_down:
			message += str(order)	

		message += str(master_id)
		
		self.__send(message,MASTER_TO_SLAVE_PORT)
			
	def receive_from_master(self):
		message = self.__read_message(MASTER_TO_SLAVE_PORT)

		if message is not None:

			for floor in range (0,N_FLOORS):
				self.__master_message['orders_up'][floor] = int(message[floor])
				self.__master_message['orders_down'][floor] = int(message[N_FLOORS+floor])

			self.__master_message['master_id'] = int(message[N_FLOORS*2])

			return self.__master_message

	def receive_from_slave(self):				
		message = self.__read_message(SLAVE_TO_MASTER_PORT)
		
		if message is not None:

			for floor in range (0,N_FLOORS):
					self.__slave_message['buttons_up'][floor] = int(message[floor])
					self.__slave_message['buttons_down'][floor] = int(message[N_FLOORS+floor]) 	

			self.__slave_message['slave_id'] = int(message[N_FLOORS*2])
			self.__slave_message['last_floor'] = int(message[N_FLOORS*2 + 1])
			self.__slave_message['next_floor'] = int(message[N_FLOORS*2 + 2])
			self.__slave_message['direction'] = int(message[N_FLOORS*2 + 3])

			return self.__slave_message

	def __send(self, data, port):
		try:
			send = ('<broadcast>', port)
			udp = socket(AF_INET, SOCK_DGRAM)
			udp.setsockopt(SOL_SOCKET, SO_BROADCAST, 1)

			###### MESSAGE IN FORMAT '<message_length;message>' FOR ERRORCHECK ######
			message = '<%s;%s>' % (str(len(data)), data)

			udp.sendto(message, send)
			udp.close()
			with self.__is_connected_to_network_key:
				self.__is_connected_to_network = True

		except IOError as error:
			print error
			print "MessageHandler.__send: Failed. Network down?"
			with self.__is_connected_to_network_key:
				self.__is_connected_to_network = False
			print "Sleeping 1 sec.."
			time.sleep(1)

	def __read_message(self,port):			
			if port == MASTER_TO_SLAVE_PORT:
				if self.__buffering_slave_messages_thread_started is not True:
					self.__start_thread(self.__thread_buffering_slave_messages)
				
				with self.__receive_buffer_slave_key:
					if self.__receive_buffer_slave: 
						return self.__receive_buffer_slave.pop(0)
					else:
						return None

			elif port == SLAVE_TO_MASTER_PORT: 
				if self.__buffering_master_messages_thread_started is not True:
					self.__start_thread(self.__thread_buffering_master_messages)

				with self.__receive_buffer_master_key:
					if self.__receive_buffer_master: 
						return self.__receive_buffer_master.pop(0)
					else:
						return None

	def __start_thread(self,thread):
			try:
				thread.daemon = True
				thread.start()

			except StandardError as error:
				print error
				print "MessageHandler.__start_thread(): Thread: %s operation failed" % (thread.name)
				interrupt_main()

	def __buffering_master_messages_thread(self):
		try:
			self.__buffering_master_messages_thread_started = True

			try:
				port = ('', SLAVE_TO_MASTER_PORT)
				udp = socket(AF_INET, SOCK_DGRAM)
				udp.bind(port)
				udp.setsockopt(SOL_SOCKET, SO_BROADCAST, 1)

			except IOError as error:
				print error
				print "MessageHandler.__buffering_master_messages_thread:"
				print "Failed setting up udp sockets"
				interrupt_main()

			while True:
				try:
					data, address = udp.recvfrom(1024)

				except IOError as error:
					print error
					print "MessageHandler.__buffering_master_messages_thread:"
					print "udp.recvfrom(1024) failed!"
					print "Sleeping 1 sec.."
					time.sleep(1)
				
				message = self.__errorcheck(data)

				if message is not None:
					with self.__receive_buffer_master_key:
						if message in self.__receive_buffer_master:
							pass
						else:
							self.__receive_buffer_master.append(message)

		except StandardError as error:
			print error
			print "MessageHandler.__buffering_master_messages"
			interrupt_main()

	def __buffering_slave_messages_thread(self):
		try:
			self.__buffering_slave_messages_thread_started = True

			try:
				port = ('', MASTER_TO_SLAVE_PORT)
				udp = socket(AF_INET, SOCK_DGRAM)
				udp.bind(port)
				udp.setsockopt(SOL_SOCKET, SO_BROADCAST, 1)

			except IOError as error:
				print error
				print "MessageHandler.__buffering_slave_messages_thread:"
				print "Failed setting up udp sockets"
				interrupt_main()
			
			while True:
				try:
					data, address = udp.recvfrom(1024)

				except IOError as error:
					print error
					print "MessageHandler.__buffering_slave_messages_thread:"
					print "udp.recvfrom(1024) failed!"
					print "Sleeping 1 sec.."
					time.sleep(1)

				message = self.__errorcheck(data)

				if message is not None:
					self.__timeout_no_active_master = time.time() + MASTER_TIMEOUT
					with self.__no_active_master_key:
						self.__no_active_master = False

					with self.__receive_buffer_slave_key:
						if message in self.__receive_buffer_slave:
							pass
						else:	
							self.__receive_buffer_slave.append(message)

		except StandardError as error:
			print error
			print "MessageHandler.__buffering_slave_messages"
			interrupt_main()

	def __master_alive_thread(self):
		try:
			__master_alive_thread_watchdog = watchdogs.ThreadWatchdog(1,"watchdog event: MessageHandler.__master_alive_thread")
			__master_alive_thread_watchdog.StartWatchdog()

			self.__master_alive_thread_started = True

			while True:				
				time.sleep(TICK*100)
				__master_alive_thread_watchdog.PetWatchdog()

				if self.__timeout_no_active_master < time.time():
					with self.__no_active_master_key:
						self.__no_active_master = True

		except StandardError as error:
			print error
			print "MessageHandler.__master_alive"
			interrupt_main()

	def __errorcheck(self,data):

		###### CHECKS THAT THE MESSAGE HAS THE FORMAT '<provided_message_length;message>' ######
		if (data[0] == '<') and (data[len(data) -1] == '>'):
			character_counter = 1
			separator_found = False
			separator_position = 0

			for character in data:
				if (character == ";") and (separator_found == False):
					separator_position = character_counter
					separator_found = True
				character_counter += 1

			measured_message_length = str(len(data) - separator_position - 1)
			provided_message_length = str()

			for character in range(1, separator_position - 1):
				provided_message_length += data[character]

			if (provided_message_length == measured_message_length) and (separator_found == True):
				message = str()
				for character in range(separator_position,len(data) - 1):
					message += data[character]
				return message
			else:
				return None
		else:
			return None
