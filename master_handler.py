from constants import MASTER_TO_MASTER_PORT,MASTER_BUTTON_ORDERS_PORT, N_ELEVATORS, N_FLOORS, LAST_FLOOR, NEXT_FLOOR, DIRECTION, DIRN_STOP, DIRN_DOWN, DIRN_UP
from socket import *
from random import randint
from threading import Thread, Lock
import time 

class MasterHandler:


	def __init__(self):
		self.__elevator_positions = [ [0]*N_ELEVATORS ]*N_ELEVATORS
		self.__button_orders = [0]*N_FLOORS*2
		self.__elevator_orders = [0]*N_FLOORS*2
		self.__elevator_online = [1]*N_ELEVATORS


		self.__active_masters = [0]*N_ELEVATORS
		
		self.__active_masters_key = Lock()
		self.__master_alive_thread_started = False
		self.__thread_buffering_master_alive = Thread(target = self.__buffering_master_alive_messages, args = (),)


	def update_master_alive(self, elevator_id):
		self.__send(str(elevator_id),MASTER_TO_MASTER_PORT)


	def check_master_alive(self):	

		if self.__master_alive_thread_started is not True:
			self.__start(self.__thread_buffering_master_alive)

		for i in range(0,N_ELEVATORS):
			if self.__active_masters[i] == 1:
				return i+1
		return -1 



	def order_elevator(self, button_orders, elevator_positions, elevator_online):
		self.__button_orders = button_orders
		self.__elevator_positions = elevator_positions
		self.__elevator_online = elevator_online
					
		# UP button calls
		for floor in range(0,N_FLOORS):
			if self.__button_orders[floor] == 0:
				self.__elevator_orders[floor] = 0
			if (self.__button_orders[floor] == 1) and ((self.__elevator_orders[floor] == 0) or (self.__elevator_online[self.__elevator_orders[floor]-1] == 0)):
				elevator_priority = [0 for elevator in range(0,N_ELEVATORS)]
				for elevator in range(0,N_ELEVATORS):
					if self.__elevator_online[elevator] == 0:
						elevator_priority[elevator] = 0
					elif (self.__elevator_positions[elevator][LAST_FLOOR] == floor) and (self.__elevator_positions[elevator][NEXT_FLOOR] == floor) and ((self.__elevator_positions[elevator][DIRECTION] == DIRN_STOP) or (self.__elevator_positions[elevator][DIRECTION] == DIRN_DOWN)):
						elevator_priority[elevator] = 19
					elif (floor < N_FLOORS) and (self.__elevator_positions[elevator][LAST_FLOOR] < floor) and (self.__elevator_positions[elevator][DIRECTION] == DIRN_UP):
						elevator_priority[elevator] = 15 + (3 - abs(self.__elevator_positions[elevator][LAST_FLOOR]-floor))					
					elif (self.__elevator_positions[elevator][DIRECTION] == DIRN_STOP):
						elevator_priority[elevator] = 11 + (3 - abs(self.__elevator_positions[elevator][LAST_FLOOR]-floor))
					else:
						elevator_priority[elevator] = 1 + randint(0,9)
				#print ("Up button calls floor: %i" % floor)
				#print elevator_priority
				for elevator in range(0,N_ELEVATORS):
					if elevator == 0:
						if (self.__elevator_online[elevator] == 1):
							self.__elevator_orders[floor] = elevator+1
					elif (elevator_priority[elevator] > elevator_priority[elevator-1]) and (self.__elevator_online[elevator] == 1):
						self.__elevator_orders[floor] = elevator+1


				
		# DOWN button calls
		for floor in range(N_FLOORS,N_FLOORS*2):
			if self.__button_orders[floor] == 0:
				self.__elevator_orders[floor] = 0

			if (self.__button_orders[floor] == 1) and  ((self.__elevator_orders[floor] == 0) or (self.__elevator_online[self.__elevator_orders[floor]-1] == 0)):
				elevator_priority = [0 for elevator in range(0,N_ELEVATORS)]
				for elevator in range(0,N_ELEVATORS):
					if self.__elevator_online[elevator] == 0:
						elevator_priority[elevator] = 0
					elif (self.__elevator_positions[elevator][LAST_FLOOR] == floor-N_FLOORS) and (self.__elevator_positions[elevator][NEXT_FLOOR] == floor-N_FLOORS) and ((self.__elevator_positions[elevator][DIRECTION] == DIRN_STOP) or (self.__elevator_positions[elevator][DIRECTION] == DIRN_DOWN)):
						elevator_priority[elevator] = 19
					elif (floor-N_FLOORS > N_FLOORS) and (self.__elevator_positions[elevator][LAST_FLOOR] > floor-N_FLOORS) and (self.__elevator_positions[elevator][DIRECTION] == DIRN_DOWN):
						elevator_priority[elevator] = 15 + (3 - abs(self.__elevator_positions[elevator][LAST_FLOOR]-floor+N_FLOORS))	
					elif (self.__elevator_positions[elevator][DIRECTION] == DIRN_STOP):
						elevator_priority[elevator] = 11 + (3 - abs(self.__elevator_positions[elevator][LAST_FLOOR]-floor+N_FLOORS))	
					else:
						elevator_priority[elevator] = 1 + randint(0,9)
				#print ("Down button calls floor: %i" % (floor-N_FLOORS))
				#print elevator_priority
				for elevator in range(0,N_ELEVATORS):
					if elevator == 0:
						if (self.__elevator_online[elevator] == 1):
							self.__elevator_orders[floor] = elevator+1
					elif (elevator_priority[elevator] > elevator_priority[elevator-1]) and (self.__elevator_online[elevator] == 1):
						self.__elevator_orders[floor] = elevator+1

		return self.__elevator_orders


		
	def __buffering_master_alive_messages(self):

		last_message = 'This message will never be heard'
		self.__master_alive_thread_started = True

		port = ('', MASTER_TO_MASTER_PORT)
		udp = socket(AF_INET, SOCK_DGRAM)
		udp.bind(port)
		udp.setsockopt(SOL_SOCKET, SO_BROADCAST, 1)

		downtime = [time.time() + 3]*N_ELEVATORS
	
		while True:
			data, address = udp.recvfrom(1024)
			message = self.__errorcheck(data)
			#print "Message: " + message
			if message is not None:
				with self.__active_masters_key:
					self.__active_masters[int(message)-1] = 1		
					downtime[int(message)-1] = time.time() + 3
			
			for i in range(0,N_ELEVATORS):
				if downtime[i] < time.time():
					self.__active_masters[i] = 0

				

	def __send(self, data, port):
		send = ('<broadcast>', port)
		udp = socket(AF_INET, SOCK_DGRAM)
		udp.setsockopt(SOL_SOCKET, SO_BROADCAST, 1)
		message='<%s;%s>' % (str(len(data)), data)
		udp.sendto(message, send)
		udp.close()

	def __start(self,thread):
		thread.daemon = True # Terminate thread when "main" is finished
		thread.start()

	def __errorcheck(self,data):
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