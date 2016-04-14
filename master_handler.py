import time

from socket import socket, AF_INET, SOCK_DGRAM, SOL_SOCKET, SO_BROADCAST
from random import randint
from threading import Thread, Lock
from thread import interrupt_main

from ported_driver.constants import N_FLOORS, LAST_FLOOR, NEXT_FLOOR, DIRECTION, DIRN_STOP, DIRN_DOWN, DIRN_UP
from config_parameters import MASTER_TO_MASTER_PORT, N_ELEVATORS, MY_ID, MASTER_TIMEOUT, SLAVE_TIMEOUT
		

class MasterHandler:
	def __init__(self):

		self.__elevator_positions = [[0 for position in range(0,3)] for elevator in range(0,N_ELEVATORS)]
		self.__assigned_orders_up = [0 for floor in range(0,N_FLOORS)]
		self.__assigned_orders_down = [0 for floor in range(0,N_FLOORS)]	
		self.__masters_online = [0 for elevator in range(0,N_ELEVATORS)]
		self.__slaves_online = [0 for elevator in range(0,N_ELEVATORS)]
		self.__orders_up = [0 for floor in range(0,N_FLOORS)]
		self.__orders_down = [0 for floor in range(0,N_FLOORS)]

		self.__masters_online_key = Lock()
		self.__slaves_online_key = Lock()

		self.__alive_thread_started = False

		self.__thread_alive = Thread(target = self.__alive_thread, args = (),name = "MasterHandler.__alive_thread")
	
		self.__slave_timeouts = [time.time() + SLAVE_TIMEOUT for elevator in range(0,N_ELEVATORS)]
		
	def current_assigned_orders(self):
		return (self.__assigned_orders_up,self.__assigned_orders_down)

	def process_slave_event(self, slave_message):
		self.__update_slave_online(slave_message['slave_id'])
		
		if self.active_master() == MY_ID:
			self.__clear_completed_orders(slave_message['direction'],slave_message['last_floor'],slave_message['next_floor'])
			self.__update_elevator_position(slave_message['slave_id'],slave_message['last_floor'],slave_message['next_floor'],slave_message['direction'])			
			self.__add_new_orders(slave_message['buttons_up'],slave_message['buttons_down'])
			self.__assign_orders()

	def i_am_alive(self):			
		if self.__alive_thread_started is not True:
			self.__start(self.__thread_alive)

		self.__send(str(MY_ID),MASTER_TO_MASTER_PORT)

	def active_master(self):

		###### RETURN THE LOWEST ONLINE MASTER ID ######
		with self.__masters_online_key:
			for elevator in range(0,N_ELEVATORS):
				if self.__masters_online[elevator] == 1:
					return elevator+1
		return -1

	def __update_elevator_position(self,slave_id,last_floor,next_floor,direction):
		self.__elevator_positions[slave_id-1] = [last_floor,next_floor,direction] 
				
	def __update_slave_online(self,slave_id):
		with self.__slaves_online_key:
			self.__slaves_online[slave_id-1] = 1
			self.__slave_timeouts[slave_id-1] = time.time() + SLAVE_TIMEOUT
	
	def __clear_completed_orders(self,direction,last_floor,next_floor):
		if last_floor == next_floor:
			arrived_floor = last_floor

			if (direction == DIRN_UP) or (direction == DIRN_STOP):
				self.__orders_up[arrived_floor] = 0
			if (direction == DIRN_DOWN) or (direction == DIRN_STOP):
				self.__orders_down[arrived_floor] = 0

	def __add_new_orders(self,buttons_up,buttons_down):
		for floor in range(0,N_FLOORS):
			if buttons_up[floor] == 1: 
				self.__orders_up[floor] = 1

			if buttons_down[floor] == 1: 
				self.__orders_down[floor] = 1	

	def __assign_orders(self):

		for floor in range(0,N_FLOORS):
			with self.__slaves_online_key:
				
				###### UP ORDERS #######
				if self.__orders_up[floor] == 0:
					self.__assigned_orders_up[floor] = 0

				if (self.__orders_up[floor] == 1) and ((self.__assigned_orders_up[floor] == 0) or (self.__slaves_online[self.__assigned_orders_up[floor]-1] == 0)):
					
					###### GIVES ALL ELEVATORS A PRIORITY NUMBER FROM '0' TO '40 + N_FLOORS*40' ACCORDING TO POSITION AND DIRECTION ######
					#	   6 PRIORITY RANGES, ADDED A RANDOM NUMBER WHICH SPREADS ORDERS TO ELEVATORS WITHIN THAT AREA  				 #
					elevator_priority_up = [0 for elevator in range(0,N_ELEVATORS)]
					for elevator in range(0,N_ELEVATORS):
						if self.__slaves_online[elevator] == 0:
							elevator_priority_up[elevator] = 0
						elif (self.__elevator_positions[elevator][LAST_FLOOR] == floor) and (self.__elevator_positions[elevator][NEXT_FLOOR] == floor) and ((self.__elevator_positions[elevator][DIRECTION] == DIRN_STOP) or (self.__elevator_positions[elevator][DIRECTION] == DIRN_UP)):
							elevator_priority_up[elevator] = 40 + N_FLOORS*40
						elif (self.__elevator_positions[elevator][LAST_FLOOR] < floor) and (self.__elevator_positions[elevator][DIRECTION] == DIRN_UP):
							elevator_priority_up[elevator] = 30 + N_FLOORS*30 + (N_FLOORS - abs(self.__elevator_positions[elevator][LAST_FLOOR] - floor))*10 + randint(0,9)
						elif (floor == 0) and (self.__elevator_positions[elevator][DIRECTION] == DIRN_DOWN):
							elevator_priority_up[elevator] = 20 + N_FLOORS*20 + (N_FLOORS - abs(self.__elevator_positions[elevator][LAST_FLOOR] - floor))*10 + randint(0,9)
						elif (self.__elevator_positions[elevator][DIRECTION] == DIRN_STOP):
							elevator_priority_up[elevator] = 10 + N_FLOORS*10 + (N_FLOORS - abs(self.__elevator_positions[elevator][LAST_FLOOR] - floor))*10 + randint(0,9)
						else:
							elevator_priority_up[elevator] = 1 + randint(0,9)

					###### ASSIGNS THE ORDER TO THE ELEVATOR WITH HIGHEST PRIORITY NUMBER ######
					for elevator in range(0,N_ELEVATORS):
						if elevator == 0:
							self.__assigned_orders_up[floor] = elevator + 1
						elif (elevator_priority_up[elevator] > elevator_priority_up[self.__assigned_orders_up[floor]-1]) and (self.__slaves_online[elevator] == 1):
							self.__assigned_orders_up[floor] = elevator + 1
					
				###### DOWN ORDERS ######
				if self.__orders_down[floor] == 0:
					self.__assigned_orders_down[floor] = 0

				if (self.__orders_down[floor] == 1) and  ((self.__assigned_orders_down[floor] == 0) or (self.__slaves_online[self.__assigned_orders_down[floor]-1] == 0)):

					###### GIVES ALL ELEVATORS A PRIORITY NUMBER FROM '0' TO '40 + N_FLOORS*40' ACCORDING TO POSITION AND DIRECTION ######
					#	   6 PRIORITY RANGES, ADDED A RANDOM NUMBER WHICH SPREADS ORDERS TO ELEVATORS WITHIN THAT AREA  				 #
					elevator_priority_down = [0 for elevator in range(0,N_ELEVATORS)]
					for elevator in range(0,N_ELEVATORS):
						if self.__slaves_online[elevator] == 0:
							elevator_priority_down[elevator] = 0
						elif (self.__elevator_positions[elevator][LAST_FLOOR] == floor) and (self.__elevator_positions[elevator][NEXT_FLOOR] == floor) and ((self.__elevator_positions[elevator][DIRECTION] == DIRN_STOP) or (self.__elevator_positions[elevator][DIRECTION] == DIRN_DOWN)):
							elevator_priority_down[elevator] = 40 + N_FLOORS*40
						elif (self.__elevator_positions[elevator][LAST_FLOOR] > floor) and (self.__elevator_positions[elevator][DIRECTION] == DIRN_DOWN):
							elevator_priority_down[elevator] = 30 + N_FLOORS*30 + (N_FLOORS - abs(self.__elevator_positions[elevator][LAST_FLOOR] - floor))*10 + randint(0,9)
						elif (floor == N_FLOORS-1) and (self.__elevator_positions[elevator][DIRECTION] == DIRN_UP):
							elevator_priority_down[elevator] = 20 + N_FLOORS*20 + (N_FLOORS - abs(self.__elevator_positions[elevator][LAST_FLOOR] - floor))*10 + randint(0,9)	
						elif (self.__elevator_positions[elevator][DIRECTION] == DIRN_STOP):	
							elevator_priority_down[elevator] = 10 + N_FLOORS*10 + (N_FLOORS - abs(self.__elevator_positions[elevator][LAST_FLOOR] - floor))*10 + randint(0,9)
						else:
							elevator_priority_down[elevator] = 1 + randint(0,9)

					###### ASSIGNS THE ORDER TO THE ELEVATOR WITH HIGHEST PRIORITY NUMBER ######
					for elevator in range(0,N_ELEVATORS):
						if elevator == 0:
							self.__assigned_orders_down[floor] = elevator + 1
						elif (elevator_priority_down[elevator] > elevator_priority_down[self.__assigned_orders_down[floor]-1]) and (self.__slaves_online[elevator] == 1):
							self.__assigned_orders_down[floor] = elevator + 1

	def __alive_thread(self):
		try:
			self.__alive_thread_started = True
			master_timeouts = [time.time() + MASTER_TIMEOUT for elevator in range(0,N_ELEVATORS)]

			try:
				port = ('', MASTER_TO_MASTER_PORT)
				udp = socket(AF_INET, SOCK_DGRAM)
				udp.bind(port)
				udp.setsockopt(SOL_SOCKET, SO_BROADCAST, 1)

			except IOError as error:
				print error
				print "MasterHandler.__alive_message_handler:"
				print "Failed setting up udp sockets"
				interrupt_main()

			while True:
				try:
					data, address = udp.recvfrom(1024)

				except IOError as error:
					print error
					print "MasterHandler.__alive_message_handler:"
					print "udp.recvfrom(1024) failed!"
					print "Sleeping 1 sec.."
					time.sleep(1)

				master_id = self.__errorcheck(data)
	
				###### UPDATE LIST OF ONLINE MASTERS ######
				if master_id is not None:
					with self.__masters_online_key:
						self.__masters_online[int(master_id)-1] = 1	
						master_timeouts[int(master_id)-1] = time.time() + MASTER_TIMEOUT
						
						###### IN CASE NETWORK IS DOWN ######
						master_id = None

				###### SET MASTERS OFFLINE IF TIMED OUT ######
				with self.__masters_online_key:
					for elevator in range(0,N_ELEVATORS):
						if master_timeouts[elevator] < time.time():
							self.__masters_online[elevator] = 0

				###### SET SLAVES OFFLINE IF TIMED OUT ######
				with self.__slaves_online_key:
					for elevator in range(0,N_ELEVATORS):
						if self.__slave_timeouts[elevator] < time.time():
							self.__slaves_online[elevator] = 0

		except StandardError as error:
			print error
			print "MasterHandler.__alive_message_handler"
			interrupt_main()
	
	
	def __send(self, data, port):
			try:
				send = ('<broadcast>', port)
				udp = socket(AF_INET, SOCK_DGRAM)
				udp.setsockopt(SOL_SOCKET, SO_BROADCAST, 1)
				
				###### MESSAGE IN FORMAT '<message_length;message>' FOR ERRORCHECK ######
				message = '<%s;%s>' % (str(len(data)), data)

				udp.sendto(message, send)
				udp.close()

			except IOError as error:
				print error
				print "MasterHandler.__send: Failed. Network down?"
				print "Sleeping 1 sec.."
				time.sleep(1)

	def __start(self,thread):
			try:
				thread.daemon = True
				thread.start()

			except StandardError as error:
				print error
				print "MasterHandler.__start(): Thread: %s operation failed" % (thread.name)
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