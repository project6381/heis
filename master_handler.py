from ported_driver.constants import N_FLOORS, LAST_FLOOR, NEXT_FLOOR, DIRECTION, DIRN_STOP, DIRN_DOWN, DIRN_UP
from config_parameters import MASTER_TO_MASTER_PORT, MASTER_BUTTON_ORDERS_PORT, N_ELEVATORS
from socket import *
from random import randint
from threading import Thread, Lock
import time 
import watchdogs
from thread import interrupt_main

		

class MasterHandler:

	def __init__(self):

		self.__elevator_positions = [[0 for position in range(0,3)] for elevator in range(0,N_ELEVATORS)]
		self.__elevator_orders_up = [0 for floor in range(0,N_FLOORS)]
		self.__elevator_orders_down = [0 for floor in range(0,N_FLOORS)]
		
		self.__masters_online = [0 for elevator in range(0,N_ELEVATORS)]
		self.__orders_id = 1
		self.__synced_elevators = [0 for elevator in range(0,N_ELEVATORS)]
		self.__slaves_online = [0 for elevator in range(0,N_ELEVATORS)]
		self.__masters_online_key = Lock()
		self.__slaves_online_key = Lock()
		self.__order_id_key = Lock()
		self.__alive_thread_started = False
		self.__timeout_thread_started = False
		self.__thread_alive = Thread(target = self.__alive_thread, args = (),name = "Buffering master alive thread")
	
		self.__orders_up = [0 for floor in range(0,N_FLOORS)]
		self.__orders_down = [0 for floor in range(0,N_FLOORS)]
		self.__last_orders_up = [0 for floor in range(0,N_FLOORS)]
		self.__last_orders_down = [0 for floor in range(0,N_FLOORS)]

		self.__downtime_order_id = time.time() + 2
		self.__downtime_slaves_online = [time.time() + 2 for elevator in range(0,N_ELEVATORS)]
		self.__timeout_order_id = 0

	def get_orders(self):
		with self.__order_id_key:
			return (self.__elevator_orders_up,self.__elevator_orders_down,self.__orders_id)

	def update_master_alive(self, elevator_id):			
		###### START THREADS IF NOT ALREADY RUNNING ######
		if self.__alive_thread_started is not True:
			self.__start(self.__thread_alive)

		self.__send(str(elevator_id),MASTER_TO_MASTER_PORT)



	def update_elevator_position(self,slave_id,last_floor,next_floor,direction):
		self.__elevator_positions[slave_id-1] = [last_floor,next_floor,direction] 
				
	def update_elevator_online(self,slave_id):
		with self.__slaves_online_key:
			self.__slaves_online[slave_id-1] = 1
			self.__downtime_slaves_online[slave_id-1] = time.time() + 1
	
	def check_master_alive(self):	
		###### RETURN THE LOWEST ELEVATOR ID ######
		with self.__masters_online_key:
			for elevator in range(0,N_ELEVATORS):
				if self.__masters_online[elevator] == 1:
					return elevator+1
		return -1

	def clear_completed_orders(self,direction,last_floor,next_floor):
		if last_floor == next_floor:
			arrived = last_floor
			if (direction == DIRN_UP) or (direction == DIRN_STOP):
				self.__orders_up[arrived] = 0
			if (direction == DIRN_DOWN) or (direction == DIRN_STOP):
				self.__orders_down[arrived] = 0


	def add_new_orders(self,slave_floor_up,slave_floor_down):
		for floor in range(0,N_FLOORS):
			if slave_floor_up[floor] == 1: 
				self.__orders_up[floor] = 1

		for floor in range(0,N_FLOORS):
			if slave_floor_down[floor] == 1: 
				self.__orders_down[floor] = 1	

	def update_sync_state(self,orders_id,slave_id):				
		if self.__orders_id == orders_id:
			self.__synced_elevators[slave_id-1] = 1

		self.__slaves_online[slave_id-1] = 1
		self.__downtime_slaves_online[slave_id-1] = time.time() + 1
		active_slaves = self.__slaves_online.count(1)

		###### UPDATES ORDERS WHEN ALL ACTIVE SLAVES ARE SYNCED OR TIMED OUT ######
		if ( (self.__orders_up != self.__last_orders_up) or (self.__orders_down != self.__last_orders_down) ) and (active_slaves == self.__synced_elevators.count(1) or self.__timeout_order_id == 1):
			self.__orders_id += 1
			if self.__orders_id > 9999: 
				self.__orders_id = 1
			self.__last_orders_up = self.__orders_up[:]
			self.__last_orders_down = self.__orders_down[:]
			self.__downtime_order_id = time.time() + 2
			self.__timeout_order_id = 0
			
		self.__assign_orders()


	def __assign_orders(self):

		#self.__elevator_positions = elevator_positions
		#self.__slaves_online = elevator_online
					
		###### ASSIGNS ORDERS TO ELEVATORS ######
		for floor in range(0,N_FLOORS):
			###### UP ORDERS #######
			if self.__last_orders_up[floor] == 0:
				self.__elevator_orders_up[floor] = 0
			with self.__slaves_online_key:
				if (self.__last_orders_up[floor] == 1) and ((self.__elevator_orders_up[floor] == 0) or (self.__slaves_online[self.__elevator_orders_up[floor]-1] == 0)):
					###### GIVES ALL ELEVATORS A PRIORITY NUMBER ACCORDING TOO POSITION ######
					elevator_priority_up = [0 for elevator in range(0,N_ELEVATORS)]
					for elevator in range(0,N_ELEVATORS):
						if self.__slaves_online[elevator] == 0:
							elevator_priority_up[elevator] = 0
						elif (self.__elevator_positions[elevator][LAST_FLOOR] == floor) and (self.__elevator_positions[elevator][NEXT_FLOOR] == floor) and ((self.__elevator_positions[elevator][DIRECTION] == DIRN_STOP) or (self.__elevator_positions[elevator][DIRECTION] == DIRN_UP)):
							elevator_priority_up[elevator] = 40 + N_FLOORS*40 + randint(0,9)
						elif (self.__elevator_positions[elevator][LAST_FLOOR] < floor) and (self.__elevator_positions[elevator][DIRECTION] == DIRN_UP):
							elevator_priority_up[elevator] = 30 + N_FLOORS*30 + (N_FLOORS - abs(self.__elevator_positions[elevator][LAST_FLOOR] - floor))*10 + randint(0,9)
						elif (floor == 0) and (self.__elevator_positions[elevator][DIRECTION] == DIRN_DOWN):
							elevator_priority_up[elevator] = 20 + N_FLOORS*20 + (N_FLOORS - abs(self.__elevator_positions[elevator][LAST_FLOOR] - floor))*10 + randint(0,9)
						elif (self.__elevator_positions[elevator][DIRECTION] == DIRN_STOP):
							if N_FLOORS < 7:
								elevator_priority_up[elevator] = 10 + N_FLOORS*10 + randint(0,N_FLOORS*10)
							else:
								elevator_priority_up[elevator] = 10 + N_FLOORS*10 + (N_FLOORS - abs(self.__elevator_positions[elevator][LAST_FLOOR] - floor))*10 + randint(0,9)
						else:
							elevator_priority_up[elevator] = 1 + randint(0,9)

					###### GIVES THE ORDER TO THE ELEVATOR WITH HIGHEST PRIORITY NUMBER ######
					for elevator in range(0,N_ELEVATORS):
						if elevator == 0:
							if (self.__slaves_online[elevator] == 1):
								self.__elevator_orders_up[floor] = elevator + 1
						elif (elevator_priority_up[elevator] > elevator_priority_up[elevator-1]) and (self.__slaves_online[elevator] == 1):
							self.__elevator_orders_up[floor] = elevator + 1
					
				###### DOWN ORDERS ######
				if self.__last_orders_down[floor] == 0:
					self.__elevator_orders_down[floor] = 0

				if (self.__last_orders_down[floor] == 1) and  ((self.__elevator_orders_down[floor] == 0) or (self.__slaves_online[self.__elevator_orders_down[floor]-1] == 0)):
					###### GIVES ALL ELEVATORS A PRIORITY NUMBER ACCORDING TOO POSITION ######
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
							if N_FLOORS < 7:
								elevator_priority_down[elevator] = 10 + N_FLOORS*10 + randint(0,N_FLOORS*10)
							else:		
								elevator_priority_down[elevator] = 10 + N_FLOORS*10 + (N_FLOORS - abs(self.__elevator_positions[elevator][LAST_FLOOR] - floor))*10 + randint(0,9)
						else:
							elevator_priority_down[elevator] = 1 + randint(0,9)

					###### GIVES THE ORDER TO THE ELEVATOR WITH HIGHEST PRIORITY NUMBER ######
					for elevator in range(0,N_ELEVATORS):
						if elevator == 0:
							if (self.__slaves_online[elevator] == 1):
								self.__elevator_orders_down[floor] = elevator + 1
						elif (elevator_priority_down[elevator] > elevator_priority_down[elevator-1]) and (self.__slaves_online[elevator] == 1):
							self.__elevator_orders_down[floor] = elevator + 1



		

	def __alive_thread(self):
		try:
			###### SET THREAD STARTED FLAG  ######
			self.__alive_thread_started = True
			downtime_masters_online = [time.time() + 2 for elevator in range(0,N_ELEVATORS)]


			###### SETTING UP LOCAL VARIABLES  ######
			#downtime = [time.time() + 3 for elevator in range(0,N_ELEVATORS)]
			last_message = 'This message will never be heard'

			###### SETTING UP UDP SOCKET ######
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

				###### RECIEVE AND CHECK ######
				try:
					data, address = udp.recvfrom(1024)

				except IOError as error:
					print error
					print "MasterHandler.__alive_message_handler:"
					print "udp.recvfrom(1024) failed!"
					
					#######################################only for testing ####################################
					print "Sleeping 1 sec.."
					time.sleep(1)
					#############################################################################################


				master_id = self.__errorcheck(data)
	
				###### UPDATE LIST OF ACTIVE MASTERS ######
				if master_id is not None:
					with self.__masters_online_key:
						self.__masters_online[int(master_id)-1] = 1
						print self.__masters_online	
						downtime_masters_online[int(master_id)-1] = time.time() + 2
						# In case network is down #
						master_id = None

				with self.__masters_online_key:
					for elevator in range(0,N_ELEVATORS):
						if downtime_masters_online[elevator] < time.time():
							self.__masters_online[elevator] = 0

				with self.__slaves_online_key:
					for elevator in range(0,N_ELEVATORS):
						if self.__downtime_slaves_online[elevator] < time.time():
							self.__slaves_online[elevator] = 0

				with self.__order_id_key:
					if self.__downtime_order_id < time.time():
						self.__timeout_order_id = 1	

		except StandardError as error:
			print error
			print "MasterHandler.__alive_message_handler"
			interrupt_main()
	
	
	def __send(self, data, port):
			try:
				send = ('<broadcast>', port)
				udp = socket(AF_INET, SOCK_DGRAM)
				udp.setsockopt(SOL_SOCKET, SO_BROADCAST, 1)
				message = '<%s;%s>' % (str(len(data)), data)
				udp.sendto(message, send)
				udp.close()

			except IOError as error:
				print error
				print "MasterHandler.__send: Failed. Network down?"
				#######################################only for testing ####################################
				print "Sleeping 1 sec.."
				time.sleep(1)
				#############################################################################################

	def __start(self,thread):
			try:
				thread.daemon = True # Terminate thread when "main" is finished
				thread.start()
			except StandardError as error:
				print error
				print "MasterHandler.__start(): Thread: %s operation failed" % (thread.name)
				interrupt_main()

	def __errorcheck(self,data):
		###### CHECKS THAT THE MESSAGE IS FOR THIS SYSTEM # WITHOUT OBVIOUS ERRORS ######
		if data[0] == '<' and data[len(data) -1] == '>':
			counter = 1
			separator = False
			separator_pos = 0

			for char in data:
				if char == ";" and separator == False:
					separator_pos = counter
					separator = True
				counter += 1

			message_length = str(len(data) - separator_pos - 1)
			test_length = str()

			for n in range(1, separator_pos - 1):
				test_length += data[n]

			if test_length == message_length and separator == True:
				message = str()
				for n in range(separator_pos,len(data) - 1):
					message += data[n]
				return message
			else:
				return None
		else:
			return None