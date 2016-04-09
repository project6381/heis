from constants import MASTER_TO_MASTER_PORT,MASTER_BUTTON_ORDERS_PORT, N_ELEVATORS, N_FLOORS, LAST_FLOOR, NEXT_FLOOR, DIRECTION, DIRN_STOP, DIRN_DOWN, DIRN_UP
from socket import *
from random import randint
from threading import Thread, Lock
import time 
import watchdogs
from thread import interrupt_main

		

class MasterHandler:

	def __init__(self):
		self.__elevator_positions = [ [0]*N_ELEVATORS ]*N_ELEVATORS
		self.__button_orders = [0]*N_FLOORS*2
		self.__elevator_orders = [0]*N_FLOORS*2
		self.__elevator_orders_up = [0]*N_FLOORS
		self.__elevator_orders_down = [0]*N_FLOORS

		self.__active_masters = [0]*N_ELEVATORS
		self.__orders_id = 1
		self.__synced_elevators = [0]*N_ELEVATORS
		self.__elevator_online = [0]*N_ELEVATORS
		self.__active_masters_key = Lock()
		self.__master_alive_thread_started = False
		self.__thread_buffering_master_alive = Thread(target = self.__master_alive_message_handler, args = (),)

		self.__orders_up = [0]*N_FLOORS
		self.__orders_down = [0]*N_FLOORS
		self.__last_orders_up = [0]*N_FLOORS
		self.__last_orders_down = [0]*N_FLOORS

		self.__downtime_order_id = time.time() + 2
		self.__downtime_elevator_online = [time.time() + 3]*N_ELEVATORS
		self.__timeout_active_slaves = 0


	def get_orders(self):
		#with watchdogs.WatchdogTimer(1):
			return (self.__elevator_orders[0:4],self.__elevator_orders[4:8],self.__orders_id)

	def update_master_alive(self, elevator_id):
		#with watchdogs.WatchdogTimer(1):
			self.__send(str(elevator_id),MASTER_TO_MASTER_PORT)

	def update_elevator_position(self,slave_id,last_floor,next_floor,direction):
		#with watchdogs.WatchdogTimer(1):
			self.__elevator_positions[slave_id-1] = [last_floor,next_floor,direction] 
				
	def update_elevator_online(self,slave_id):
		#with watchdogs.WatchdogTimer(1):
			self.__elevator_online[slave_id-1] = 1
			self.__downtime_elevator_online[slave_id-1] = time.time() + 1
		
	def check_master_alive(self):	
		#with watchdogs.WatchdogTimer(1):
			if self.__master_alive_thread_started is not True:
				self.__start(self.__thread_buffering_master_alive)

			for i in range(0,N_ELEVATORS):
				if self.__active_masters[i] == 1:
					return i+1
			return -1 

	def clear_completed_orders(self,direction,last_floor,next_floor):
		#with watchdogs.WatchdogTimer(1):
			if last_floor == next_floor:
				arrived = last_floor
				if (direction == DIRN_UP) or (direction == DIRN_STOP):
					self.__orders_up[arrived] = 0
				if (direction == DIRN_DOWN) or (direction == DIRN_STOP):
					self.__orders_down[arrived] = 0


	def add_new_orders(self,slave_floor_up,slave_floor_down):
		#with watchdogs.WatchdogTimer(1):
			for i in range(0,N_FLOORS):
				if slave_floor_up[i] == 1: 
					self.__orders_up[i] = 1

			for i in range(0,N_FLOORS):
				if slave_floor_down[i] == 1: 
					self.__orders_down[i] = 1	

	def update_sync_state(self,orders_id,slave_id):
		#with watchdogs.WatchdogTimer(1):			
			if self.__orders_id == orders_id:
				self.__synced_elevators[slave_id-1] = 1

			self.__elevator_online[slave_id-1] = 1
			self.__downtime_elevator_online[slave_id-1] = time.time() + 1
			active_slaves = self.__elevator_online.count(1)

			
			if ( (self.__orders_up != self.__last_orders_up) or (self.__orders_down != self.__last_orders_down) ) and (active_slaves == self.__synced_elevators.count(1) or self.__timeout_active_slaves == 1): # and (0 not in elevators_queue_id):
				#print '1111111111111111111111111111111111'
				self.__orders_id += 1
				if self.__orders_id > 9999: 
					self.__orders_id = 1
				self.__last_orders_up = self.__orders_up[:]
				self.__last_orders_down = self.__orders_down[:]
				self.__downtime_order_id = time.time() + 2
				self.__timeout_active_slaves = 0

				
			print self.__orders_up + self.__orders_down				
			self.__assign_orders()


	def __assign_orders(self):
		#with watchdogs.WatchdogTimer(1):
			#self.__elevator_positions = elevator_positions
			#self.__elevator_online = elevator_online
						
			
			for floor in range(0,N_FLOORS):
			# UP button calls
				if self.__last_orders_up[floor] == 0:
					self.__elevator_orders_up[floor] = 0

				if (self.__last_orders_up[floor] == 1) and ((self.__elevator_orders_up[floor] == 0) or (self.__elevator_online[self.__elevator_orders_up[floor]-1] == 0)):
					elevator_priority_up = [0]*N_ELEVATORS
					for elevator in range(0,N_ELEVATORS):
						if self.__elevator_online[elevator] == 0:
							elevator_priority_up[elevator] = 0
						elif (self.__elevator_positions[elevator][LAST_FLOOR] == floor) and (self.__elevator_positions[elevator][NEXT_FLOOR] == floor) and ((self.__elevator_positions[elevator][DIRECTION] == DIRN_STOP) or (self.__elevator_positions[elevator][DIRECTION] == DIRN_UP)):
							elevator_priority_up[elevator] = 5 + N_FLOORS*5
						elif (self.__elevator_positions[elevator][LAST_FLOOR] < floor) and (self.__elevator_positions[elevator][DIRECTION] == DIRN_UP):
							elevator_priority_up[elevator] = 4 + N_FLOORS*4 + (N_FLOORS - abs(self.__elevator_positions[elevator][LAST_FLOOR] - floor))
						elif (floor == 0) and (self.__elevator_positions[elevator][DIRECTION] == DIRN_DOWN):
							elevator_priority_up[elevator] = 3 + N_FLOORS*3 + (N_FLOORS - abs(self.__elevator_positions[elevator][LAST_FLOOR] - floor))
						elif (self.__elevator_positions[elevator][DIRECTION] == DIRN_STOP):
							elevator_priority_up[elevator] = 2 + N_FLOORS*2 + (N_FLOORS - abs(self.__elevator_positions[elevator][LAST_FLOOR] - floor))
						else:
							elevator_priority_up[elevator] = 1 + randint(0,N_FLOORS)
					#print ("Up button calls floor: %i" % floor)
					#print elevator_priority
					for elevator in range(0,N_ELEVATORS):
						if elevator == 0:
							if (self.__elevator_online[elevator] == 1):
								self.__elevator_orders_up[floor] = elevator+1
						elif (elevator_priority_up[elevator] > elevator_priority_up[elevator-1]) and (self.__elevator_online[elevator] == 1):
							self.__elevator_orders_up[floor] = elevator+1
					
			# DOWN button calls
				if self.__last_orders_down[floor] == 0:
					self.__elevator_orders_down[floor] = 0

				if (self.__last_orders_down[floor] == 1) and  ((self.__elevator_orders_down[floor] == 0) or (self.__elevator_online[self.__elevator_orders_down[floor]-1] == 0)):
					elevator_priority_down = [0]*N_ELEVATORS
					for elevator in range(0,N_ELEVATORS):
						if self.__elevator_online[elevator] == 0:
							elevator_priority_down[elevator] = 0
						elif (self.__elevator_positions[elevator][LAST_FLOOR] == floor) and (self.__elevator_positions[elevator][NEXT_FLOOR] == floor) and ((self.__elevator_positions[elevator][DIRECTION] == DIRN_STOP) or (self.__elevator_positions[elevator][DIRECTION] == DIRN_DOWN)):
							elevator_priority_down[elevator] = 5 + N_FLOORS*5
						elif (self.__elevator_positions[elevator][LAST_FLOOR] > floor) and (self.__elevator_positions[elevator][DIRECTION] == DIRN_DOWN):
							elevator_priority_down[elevator] = 4 + N_FLOORS*4 + (N_FLOORS - abs(self.__elevator_positions[elevator][LAST_FLOOR] - floor))
						elif (floor == N_FLOORS-1) and (self.__elevator_positions[elevator][DIRECTION] == DIRN_UP):
							elevator_priority_down[elevator] = 3 + N_FLOORS*3 + (N_FLOORS - abs(self.__elevator_positions[elevator][LAST_FLOOR] - floor))	
						elif (self.__elevator_positions[elevator][DIRECTION] == DIRN_STOP):
							elevator_priority_down[elevator] = 2 + N_FLOORS*2 + (N_FLOORS - abs(self.__elevator_positions[elevator][LAST_FLOOR] - floor))	
						else:
							elevator_priority_down[elevator] = 1 + randint(0,N_FLOORS)
					#print ("Down button calls floor: %i" % (floor-N_FLOORS))
					#print elevator_priority
					for elevator in range(0,N_ELEVATORS):
						if elevator == 0:
							if (self.__elevator_online[elevator] == 1):
								self.__elevator_orders_down[floor] = elevator+1
						elif (elevator_priority_down[elevator] > elevator_priority_down[elevator-1]) and (self.__elevator_online[elevator] == 1):
							self.__elevator_orders_down[floor] = elevator+1


			self.__elevator_orders = self.__elevator_orders_up[:] + self.__elevator_orders_down[:] #quick fix
			#return self.__elevator_orders


		
	def __master_alive_message_handler(self):
		#try:
			#__master_alive_message_handler_watchdog = watchdogs.ThreadWatchdog(1,"watchdog event: MasterHandler.__master_alive_message_handler_watchdog")
			#__master_alive_message_handler_watchdog.StartWatchdog()

			last_message = 'This message will never be heard'
			self.__master_alive_thread_started = True

			port = ('', MASTER_TO_MASTER_PORT)
			udp = socket(AF_INET, SOCK_DGRAM)
			udp.bind(port)
			udp.setsockopt(SOL_SOCKET, SO_BROADCAST, 1)

			downtime = [time.time() + 3]*N_ELEVATORS
		
			while True:
				#__master_alive_message_handler_watchdog.PetWatchdog()
				data, address = udp.recvfrom(1024)
				message = self.__errorcheck(data)
				if message is not None:
					with self.__active_masters_key:
						self.__active_masters[int(message)-1] = 1		
						downtime[int(message)-1] = time.time() + 3
				
				for i in range(0,N_ELEVATORS):
					if downtime[i] < time.time():
						self.__active_masters[i] = 0

				

				''' quick fix '''
				for i in range(0,N_ELEVATORS):
					if self.__downtime_elevator_online[i] < time.time():
						self.__elevator_online[i] = 0


				if self.__downtime_order_id < time.time():
					for i in range(0,N_ELEVATORS):
						self.__timeout_active_slaves = 1

		#except StandardError as error:
		#	print error
		#	print "MasterHandler.__master_alive_message_handler"
		#	interrupt_main()


	def __send(self, data, port):
		#with watchdogs.WatchdogTimer(1):
			send = ('<broadcast>', port)
			udp = socket(AF_INET, SOCK_DGRAM)
			udp.setsockopt(SOL_SOCKET, SO_BROADCAST, 1)
			message='<%s;%s>' % (str(len(data)), data)
			udp.sendto(message, send)
			udp.close()

	def __start(self,thread):
		#with watchdogs.WatchdogTimer(1):
			thread.daemon = True # Terminate thread when "main" is finished
			thread.start()

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