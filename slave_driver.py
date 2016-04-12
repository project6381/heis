from ported_driver.elevator_interface import ElevatorInterface
from ported_driver.panel_interface import PanelInterface
from ported_driver.constants import DIRN_STOP, DIRN_UP, DIRN_DOWN, BUTTON_UP, BUTTON_DOWN, BUTTON_INTERNAL, N_FLOORS, N_BUTTONS 
from config_parameters import MY_ID, TICK
from threading import Thread, Lock
from thread import interrupt_main
import time
import pickle
import watchdogs


class SlaveDriver:
	def __init__(self):
		self.__elevator_interface = ElevatorInterface()
		self.__panel_interface = PanelInterface()
		self.__elevator_orders_key = Lock()
		self.__master_orders_key = Lock()
		self.__internal_orders_key = Lock()
		self.__floor_panel_key = Lock()
		self.__position_key = Lock()
		self.__offline_mode_key = Lock()
		self.__move_timeout_key = Lock()
		self.__move_timeout = False
		self.__elevator_orders = [[0 for button in range(0,N_BUTTONS)] for floor in range(0,N_FLOORS)]
		self.__master_orders_up = [0 for floor in range(0,N_FLOORS)]
		self.__master_orders_down = [0 for floor in range(0,N_FLOORS)]
		self.__saved_master_orders_up = [0 for floor in range(0,N_FLOORS)]
		self.__saved_master_orders_down = [0 for floor in range(0,N_FLOORS)]
		self.__internal_orders = [0 for floor in range(0,N_FLOORS)]
		self.__saved_internal_orders = [0 for floor in range(0,N_FLOORS)]
		self.__floor_panel_up = [0 for floor in range(0,N_FLOORS)]
		self.__floor_panel_down = [0 for floor in range(0,N_FLOORS)]
		self.__last_master_id = 0
		self.__offline_mode = False
		self.__position = (0,0,DIRN_STOP)
		self.__thread_run_elevator = Thread(target = self.__run_elevator_thread, args = (), name = "SlaveDriver.__run_elevator_thread")
		self.__thread_read_button = Thread(target = self.__read_button_thread, args = (), name = "SlaveDriver.__thread_read_button")
		self.__thread_set_indicators = Thread(target = self.__set_indicators_thread, args = (), name = "SlaveDriver.__thread_set_indicators")
		self.__thread_save_orders = Thread(target = self.__save_orders_thread, args = (), name = "SlaveDriver.__thread_save_orders")
		self.__start()

	
	def changing_master(self,master_id,orders_ok):
		if self.__last_master_id !=  master_id:
			self.__last_master_id = master_id
			return True
		elif orders_ok == False: 
			return True
		else:
			return False

	def master_order_run_elevator(self,master_order_up,master_order_down):
		with self.__master_orders_key:
			self.__master_orders_up = master_order_up
			self.__master_orders_down = master_order_down

	def read_saved_master_queue(self):
		with self.__master_orders_key:
			return (self.__saved_master_orders_up[:],self.__saved_master_orders_down[:])
	
	def get_floor_panel(self):
		with self.__floor_panel_key:
			return (self.__floor_panel_up[:],self.__floor_panel_down[:])		
	
	'''
	def clear_floor_panel(self,orders_up,orders_down):
		with self.__floor_panel_key:
			for floor in range (0,N_FLOORS):			
				if (orders_up[floor] != 0):
					self.__floor_panel_up[floor] = 0
				if (orders_down[floor] != 0):
					self.__floor_panel_down[floor] = 0
	'''

	def read_position(self):
		with self.__position_key:
			return self.__position

	def set_offline_mode(self,offline_mode):
		with self.__offline_mode_key:
			self.__offline_mode = offline_mode

	def read_move_timeout(self):
		with self.__move_timeout_key:
			return self.__move_timeout


	def __start(self):
		###### STARTS THE INITIAL-FUNCTIONS AND THREADS ######
		try:
			with self.__master_orders_key:
				self.__startup()
				self.__load_elevator_orders()
				self.__thread_run_elevator.daemon = True
				self.__thread_run_elevator.start()
				self.__thread_read_button.daemon = True
				self.__thread_read_button.start()
				self.__thread_set_indicators.daemon = True
				self.__thread_set_indicators.start()
				self.__thread_save_orders.daemon = True
				self.__thread_save_orders.start()

		except StandardError as error:
			print error
			print "SlaveDriver.__start"
			interrupt_main()
			
	
	def __startup(self):
		###### RUNS UP FOR 5s THEN DOWN FOR 5s # OR # UNTIL IT FINDS A FLOOR SENSOR ######
		try:
			check_floor = self.__elevator_interface.get_floor_sensor_signal()
			turn_time = time.time() + 5
			timeout_time = time.time() + 10

			while check_floor < 0:
				if turn_time > time.time():
					self.__elevator_interface.set_motor_direction(DIRN_DOWN)
					pass
				else:
					self.__elevator_interface.set_motor_direction(DIRN_UP)	
				check_floor = self.__elevator_interface.get_floor_sensor_signal()
				assert timeout_time > time.time(), "unknown error: elevator not moving"

			self.__elevator_interface.set_motor_direction(DIRN_STOP)
		except StandardError as error:
			print error
			print "SlaveDriver.__startup"
			interrupt_main()


	def __load_elevator_orders(self):
		###### READS OLD MASTER ORDERS FROM FILE ######
		try:
			with open("master_file_main", "rb") as master_file:
				(self.__master_orders_up, self.__master_orders_down) = pickle.load(master_file)
				self.__saved_master_orders_up = self.__master_orders_up[:]
				self.__saved_master_orders_down = self.__master_orders_down[:]
		except StandardError as error:
			print error
			print "SlaveDriver.__load_elevator_orders"
			print "master_file_main"
			try:
				with open("master_file_backup", "rb") as master_file:
					(self.__master_orders_up, self.__master_orders_down) = pickle.load(master_file)
					self.__saved_master_orders_up = self.__master_orders_up[:]
					self.__saved_master_orders_down = self.__master_orders_down[:]
			except StandardError as error:
				print error
				print "SlaveDriver.__load_elevator_orders"
				print "master_file_backup"

		###### ASSIGNES OLD MASTER ORDERS TO ELEVATOR ORDERS ######
		for floor in range(0,N_FLOORS):
			if self.__saved_master_orders_up[floor] == MY_ID:
				self.__elevator_orders[floor][BUTTON_UP] = 1
			if self.__saved_master_orders_down[floor] == MY_ID:
				self.__elevator_orders[floor][BUTTON_DOWN] = 1

		###### READS OLD INTERNAL ORDERS FROM FILE ######
		try:
			with open("internal_file_main", "rb") as internal_file:
				self.__internal_orders = pickle.load(internal_file)
				self.__saved_internal_orders = self.__internal_orders[:]
		except StandardError as error:
			print error
			print "SlaveDriver.__load_elevator_orders"
			print "internal_file_main"
			try:
				with open("internal_file_backup", "rb") as internal_file:
					self.__internal_orders = pickle.load(internal_file)
					self.__saved_internal_orders = self.__internal_orders[:]
			except StandardError as error:
				print error
				print "SlaveDriver.__load_elevator_orders"
				print "internal_file_backup"

		###### ASSIGNS OLD INTERNAL ORDERS TO ELEVATOR ORDERS ######
		for floor in range(0,N_FLOORS):
			self.__elevator_orders[floor][BUTTON_INTERNAL] = self.__saved_internal_orders[floor]


	def __run_elevator_thread(self):
		##### RUNS THE ELEVATOR ACCORDING TO ELEVATOR ORDERS ######
		try:
			__run_elevator_thread_watchdog = watchdogs.ThreadWatchdog(5,"watchdog event: SlaveDriver.__run_elevator_thread")
			__run_elevator_thread_watchdog.StartWatchdog()

			last_floor = 0
			next_floor = 0
			next_button = 0
			last_direction = DIRN_STOP
			direction = DIRN_STOP
			last_read_floor = -1

			while True:
				time.sleep(TICK)
				__run_elevator_thread_watchdog.PetWatchdog()

				###### DECIDES WHICH FLOOR TO GO TO NEXT ######
				elevator_orders_max = 0
				elevator_orders_min = N_FLOORS-1
				with self.__elevator_orders_key:
					for floor in range(0,N_FLOORS):
						for button in range(0,3):
								if self.__elevator_orders[floor][button] == 1:
									elevator_orders_max = max(elevator_orders_max,floor)
									elevator_orders_min = min(elevator_orders_min,floor)
									if (last_floor == next_floor) and (direction != DIRN_DOWN) and (next_floor <= elevator_orders_max):
										next_floor = floor
										next_button = button
									elif (last_floor == next_floor) and (direction != DIRN_UP) and (next_floor >= elevator_orders_min):
										next_floor = floor
										next_button = button
									elif (last_floor < next_floor) and (floor < next_floor) and (floor > last_floor) and (button != BUTTON_DOWN):
										next_floor = floor
										next_button = button
									elif (last_floor > next_floor) and (floor > next_floor) and (floor < last_floor) and (button != BUTTON_UP):
										next_floor = floor
										next_button = button
				
				if (direction == DIRN_UP) and (elevator_orders_max > 0) and (next_button == BUTTON_DOWN):
					next_floor = elevator_orders_max
				elif (direction == DIRN_DOWN) and (elevator_orders_min < N_FLOORS-1) and (next_button == BUTTON_UP):
					next_floor = elevator_orders_min

				###### READS LAST FLOOR SIGNAL ######
				read_floor = self.__elevator_interface.get_floor_sensor_signal()
				if read_floor >= 0:
					last_floor = read_floor

				###### SETS DIRECTION TO STOP WHEN ELEVATOR REACHES HIGHEST/LOWEST ELEVATOR ORDER ######
				if (direction == DIRN_UP) and (elevator_orders_max <= last_floor):
					last_direction = direction
					direction = DIRN_STOP
				elif (direction == DIRN_DOWN) and (elevator_orders_min >= last_floor):
					last_direction = direction
					direction = DIRN_STOP
				

				###### STOPS ELEVATOR AND CLEARS THE ELEVATOR ORDER ######
				if last_floor == next_floor:
					####### STOPS ELEVATOR #######	
					self.__elevator_interface.set_motor_direction(DIRN_STOP)

					###### SETS ELEVATOR POSITION ######
					with self.__position_key:
						self.__position = (last_floor,next_floor,direction)

					###### STOPS AT FLOOR FOR 1 SECOND ######
					time.sleep(1)

					###### CHECKS THAT ELEVATOR ACTUALLY STOPPED ######
					read_floor = self.__elevator_interface.get_floor_sensor_signal()
					if read_floor != last_floor:
						print "read_floor != last_floor"
						print direction
						###### RUNS ELEVATOR IN OPPOSITE DIRECTION ######
						if direction == DIRN_STOP:
							if last_direction == DIRN_UP:
								self.__elevator_interface.set_motor_direction(DIRN_DOWN)
							elif last_direction == DIRN_DOWN:
								self.__elevator_interface.set_motor_direction(DIRN_UP)
						if direction == DIRN_UP:
								self.__elevator_interface.set_motor_direction(DIRN_DOWN)
						elif direction == DIRN_DOWN:
								self.__elevator_interface.set_motor_direction(DIRN_UP)

						###### STOPS ELEVATOR WHEN IT REACHES A FLOOR ######
						while (read_floor < 0):
							read_floor = self.__elevator_interface.get_floor_sensor_signal()
						self.__elevator_interface.set_motor_direction(DIRN_STOP)

					###### CLEARS COMPLETE ELEVATOR ORDERS ######
					if read_floor == last_floor:
						if direction == DIRN_STOP:
							with self.__elevator_orders_key:
								self.__elevator_orders[next_floor][BUTTON_UP] = 0
								self.__elevator_orders[next_floor][BUTTON_DOWN] = 0
								self.__elevator_orders[next_floor][BUTTON_INTERNAL] = 0
						elif direction == DIRN_UP:
							with self.__elevator_orders_key:
								self.__elevator_orders[next_floor][BUTTON_UP] = 0
								self.__elevator_orders[next_floor][BUTTON_INTERNAL] = 0
						elif direction == DIRN_DOWN:
							with self.__elevator_orders_key:
								self.__elevator_orders[next_floor][BUTTON_DOWN] = 0
								self.__elevator_orders[next_floor][BUTTON_INTERNAL] = 0

					###### STOPS AT FLOOR FOR 1 MORE SECOND ######
					time.sleep(1)

					###### RESETS ELEVATOR MOVEMENT CHECK ######
					move_timeout = time.time() + 5

				###### RUNS ELEVATOR IN UPWARD DIRECTION ######
				elif last_floor < next_floor:
					self.__elevator_interface.set_motor_direction(DIRN_UP)
					direction = DIRN_UP

					###### SETS ELEVATOR POSITION ######
					with self.__position_key:
						self.__position = (last_floor,next_floor,direction)

					###### CHECKS THAT THE ELEVATOR IS MOVING ######
					if read_floor != last_read_floor:
						move_timeout = time.time() + 5
						last_read_floor = read_floor
					with self.__move_timeout_key:
						if move_timeout < time.time():
							self.__move_timeout = True
						else:
							self.__move_timeout = False

				###### RUNS ELEVATOR IN DOWNWARD DIRECTION ######
				elif last_floor > next_floor:
					self.__elevator_interface.set_motor_direction(DIRN_DOWN)
					direction = DIRN_DOWN

					###### SETS ELEVATOR POSITION ######
					with self.__position_key:
						self.__position = (last_floor,next_floor,direction)

					###### CHECKS THAT THE ELEVATOR IS MOVING ######
					if read_floor != last_read_floor:
						move_timeout = time.time() + 5
						last_read_floor = read_floor
					with self.__move_timeout_key:
						if move_timeout < time.time():
							self.__move_timeout = True
						else:
							self.__move_timeout = False



			
				#print " my_id:" + str(MY_ID) + " up:" + str(self.__saved_master_orders_up) + " saved_up:" + str(self.__master_orders_up) + " down:" + str(self.__saved_master_orders_down) + " saved_down" + str(self.__master_orders_down) + " internal" + str(self.__internal_orders) + " saved_internal" + str(self.__saved_internal_orders) + " orders:" + str(self.__elevator_orders) + " n:" + str(next_floor) + " l:" + str(last_floor)

		except StandardError as error:
			print error
			print "SlaveDriver.__run_elevator_thread"
			interrupt_main()


	def __read_button_thread(self):
		###### READS BUTTON PRESS ######
		try:
			__read_button_thread_watchdog = watchdogs.ThreadWatchdog(1,"watchdog event: SlaveDriver.__read_button_thread")
			__read_button_thread_watchdog.StartWatchdog()

			while True:
				time.sleep(TICK)
				__read_button_thread_watchdog.PetWatchdog()

				for floor in range (0,N_FLOORS):
					for button in range(0,3):
						if (floor == 0 and button == BUTTON_DOWN) or (floor == N_FLOORS-1 and button == BUTTON_UP):
							pass
						elif self.__panel_interface.get_button_signal(button,floor):
							###### ADDS INTERNAL BUTTON TO INTERNAL ORDERS ######
							if button == BUTTON_INTERNAL:
								with self.__internal_orders_key:
									self.__internal_orders[floor] = 1
							###### ADDS UP/DOWN BUTTON TO FLOOR PANEL LIST ###### 
							elif button == BUTTON_UP:
								with self.__floor_panel_key:
									self.__floor_panel_up[floor] = 1
							elif button == BUTTON_DOWN:
								with self.__floor_panel_key:
									self.__floor_panel_down[floor] = 1
						else:
							###### CLEARS UP/DOWN BUTTON FROM FLOOR PANEL LIST ###### 
							if button == BUTTON_UP:
								with self.__floor_panel_key:
									self.__floor_panel_up[floor] = 0
							elif button == BUTTON_DOWN:
								with self.__floor_panel_key:
									self.__floor_panel_down[floor] = 0


		except StandardError as error:
			print error
			print "SlaveDriver.__read_button_thread"
			interrupt_main()


	def __save_orders_thread(self):
		###### SAVES ORDERS TO FILES ######
		try:
			__save_orders_thread_watchdog = watchdogs.ThreadWatchdog(1,"watchdog event: SlaveDriver.__save_orders_thread")
			__save_orders_thread_watchdog.StartWatchdog()

			while True:
				time.sleep(TICK)
				__save_orders_thread_watchdog.PetWatchdog()

				###### SAVES INTERNAL ORDERS TO FILE # WITH BACKUP ######
				with self.__internal_orders_key:
					if self.__internal_orders != self.__saved_internal_orders:
						with open("internal_file_main", "wb") as internal_file:
							pickle.dump(self.__internal_orders, internal_file)

						with open("internal_file_backup", "wb") as internal_file: 
							pickle.dump(self.__internal_orders, internal_file)
						try:
							with open("internal_file_main", "rb") as internal_file:
								self.__saved_internal_orders = pickle.load(internal_file)
							assert self.__internal_orders == self.__saved_internal_orders, "unknown error: loading internal_file_main"
						except StandardError as error:
							print error
							with open("internal_file_backup", "rb") as internal_file: 
								self.__saved_internal_orders = pickle.load(internal_file)
							assert self.__internal_orders == self.__saved_internal_orders, "unknown error: loading internal_file_backup"

						###### ADDS SAVED INTERNAL ORDERS TO ELEVATOR ORDERS ######
						with self.__elevator_orders_key:
							for floor in range(0,N_FLOORS):
								if self.__saved_internal_orders[floor] == 1:
									self.__elevator_orders[floor][BUTTON_INTERNAL] = 1

					###### CLEARS COMPLETE ELEVATOR ORDERS FROM INTERNAL ORDERS ######
					with self.__elevator_orders_key:
						for floor in range(0,N_FLOORS):			
							if self.__elevator_orders[floor][BUTTON_INTERNAL] == 0:
								self.__internal_orders[floor] = 0

		
				###### SAVES MASTER ORDERS UP/DOWN TO FILE # WITH BACKUP ######				
				with self.__master_orders_key:
					if (self.__master_orders_up != self.__saved_master_orders_up) or (self.__master_orders_down != self.__saved_master_orders_down):
						with open("master_file_main", "wb") as master_file:
							pickle.dump((self.__master_orders_up, self.__master_orders_down), master_file)

						with open("master_file_backup", "wb") as master_file: 
							pickle.dump((self.__master_orders_up, self.__master_orders_down), master_file)

						try:
							with open("master_file_main", "rb") as master_file:
								(self.__saved_master_orders_up, self.__saved_master_orders_down) = pickle.load(master_file)
							assert self.__master_orders_up == self.__saved_master_orders_up, "unknown error: loading master_file_main"
							assert self.__master_orders_down == self.__saved_master_orders_down, "unknown error: loading master_file_main"
						except StandardError as error:
							print error
							with open("master_file_backup", "rb") as master_file: 
									(self.__saved_master_orders_up, self.__saved_master_orders_down) = pickle.load(master_file)
							assert self.__master_orders_up == self.__saved_master_orders_up, "unknown error: loading master_file_backup"
							assert self.__master_orders_down == self.__saved_master_orders_down, "unknown error: loading master_file_backup"


						###### ADDS SAVED MASTER ORDERS UP/DOWN WITH MY ID TO ELEVATOR ORDERS ######
						with self.__elevator_orders_key:
							for floor in range(0,N_FLOORS):
								###### UP CALLS	######
								if self.__saved_master_orders_up[floor] == MY_ID:
									self.__elevator_orders[floor][BUTTON_UP] = 1
								####################################### BURDE KANSKJE FJERNES #####################################################
								#else:
								#	self.__elevator_orders[floor][BUTTON_UP] = 0 # LAR MASTER FJERNE ORDRE
								###################################################################################################################

								###### DOWN CALLS ######
								if self.__saved_master_orders_down[floor] == MY_ID:
									self.__elevator_orders[floor][BUTTON_DOWN] = 1
								####################################### BURDE KANSKJE FJERNES #####################################################
								#else:
								#	self.__elevator_orders[floor][BUTTON_DOWN] = 0 # LAR MASTER FJERNE ORDRE
								###################################################################################################################

					###### OFFLINE MODE ######
					#print self.__offline_mode
					with self.__offline_mode_key:
						if self.__offline_mode == True:
							###### CHANGES ALL SAVED MASTER ORDERS TO MY ID ######
							for floor in range(0,N_FLOORS):
								if self.__saved_master_orders_up[floor] > 0:
									self.__master_orders_up[floor] = MY_ID
								if self.__saved_master_orders_down[floor] > 0:
									self.__master_orders_down[floor] = MY_ID

							###### CLEARS COMPLETE ELEVATOR ORDERS UP/DOWN FROM MASTER ORDERS ######
							with self.__elevator_orders_key:
								for floor in range(0,N_FLOORS):
									###### UP CALLS	######
									if (self.__saved_master_orders_up[floor] == MY_ID) and (self.__elevator_orders[floor][BUTTON_UP] == 0):
										self.__master_orders_up[floor] = 0
									###### DOWN CALLS ######
									if (self.__saved_master_orders_down[floor] == MY_ID) and (self.__elevator_orders[floor][BUTTON_DOWN] == 0):
										self.__master_orders_down[floor] = 0

		except StandardError as error:
			print error
			print "SlaveDriver.__save_orders_thread"
			interrupt_main()


	def __set_indicators_thread(self):
		try:
			__set_indicators_thread_watchdog = watchdogs.ThreadWatchdog(1,"watchdog event: SlaveDriver.__set_indicators_thread_watchdog")
			__set_indicators_thread_watchdog.StartWatchdog()

			while True:
				time.sleep(TICK)
				__set_indicators_thread_watchdog.PetWatchdog()

				###### SETS CALL INDICATORS #####
				with self.__master_orders_key:
					for floor in range(0,N_FLOORS):
						###### UP CALLS ######
						if floor != 3:
							if self.__saved_master_orders_up[floor] > 0:
								self.__panel_interface.set_button_lamp(BUTTON_UP,floor,1)
							else:
								self.__panel_interface.set_button_lamp(BUTTON_UP,floor,0)
						###### DOWN CALLS ######
						if floor != 0:
							if self.__saved_master_orders_down[floor] > 0:
								self.__panel_interface.set_button_lamp(BUTTON_DOWN,floor,1)
							else:
								self.__panel_interface.set_button_lamp(BUTTON_DOWN,floor,0)
						###### INTERNAL CALLS ######
						with self.__internal_orders_key:
							if self.__saved_internal_orders[floor] == 1:
								self.__panel_interface.set_button_lamp(BUTTON_INTERNAL,floor,1)
							else:
								self.__panel_interface.set_button_lamp(BUTTON_INTERNAL,floor,0)
																	
				###### GETS POSITION ######
				with self.__position_key:
					read_floor = self.__elevator_interface.get_floor_sensor_signal()
					(last_floor, next_floor, direction) = self.__position
				
				###### SETS OPEN DOOR INDICATOR ######
				if read_floor < 0:
					self.__panel_interface.set_door_open_lamp(0)
				elif last_floor == next_floor:
					self.__panel_interface.set_door_open_lamp(1)
				else:
					self.__panel_interface.set_door_open_lamp(0)

				###### SETS FLOOR INDICATOR ######
				self.__panel_interface.set_floor_indicator(last_floor)

		except StandardError as error:
			print error
			print "SlaveDriver.__set_indicators_thread"
			interrupt_main()

