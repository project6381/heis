from elevator_interface import ElevatorInterface
from panel_interface import PanelInterface
from constants import N_FLOORS, DIRN_STOP, DIRN_UP, DIRN_DOWN, N_BUTTONS, BUTTON_UP, BUTTON_DOWN, BUTTON_INTERNAL, MY_ID
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
		self.__assigned_orders_key = Lock()
		self.__internal_orders_key = Lock()
		self.__floor_panel_key = Lock()
		self.__elevator_orders = [[0 for button in range(0,N_BUTTONS)] for floor in range(0,N_FLOORS)]
		self.__assigned_orders_up = [0 for floor in range(0,N_FLOORS)]
		self.__assigned_orders_down = [0 for floor in range(0,N_FLOORS)]
		self.__saved_assigned_orders_up = [0 for floor in range(0,N_FLOORS)]
		self.__saved_assigned_orders_down = [0 for floor in range(0,N_FLOORS)]
		self.__internal_orders = [0 for floor in range(0,N_FLOORS)]
		self.__saved_internal_orders = [0 for floor in range(0,N_FLOORS)]
		self.__floor_panel_up = [0 for floor in range(0,N_FLOORS)]
		self.__floor_panel_down = [0 for floor in range(0,N_FLOORS)]
		self.__last_master_id = 0
		self.__position = (0,0,DIRN_STOP)
		self.__thread_run_elevator = Thread(target = self.__run_elevator, args = (),)
		self.__thread_build_queues = Thread(target = self.__build_queues, args = (),)
		self.__thread_set_indicators = Thread(target = self.__set_indicators, args = (),)
		self.__start()



	
	def changing_master(self,master_id):
		if self.__last_master_id !=  master_id:
			self.__last_master_id = master_id
			return True
		else: 
			return False


	def master_queue_elevator_run(self,master_queue):
		with self.__assigned_orders_key:
			self.__assigned_orders_up = master_queue[0:4]	#quick fix
			self.__assigned_orders_down = master_queue[4:8] #quick fix

	def read_saved_master_queue(self):
		with self.__assigned_orders_key:
			saved_master_queue = self.__saved_assigned_orders_up[:] + self.__saved_assigned_orders_down[:] #quick fix
			return saved_master_queue
	
	def get_floor_panel(self):
		with self.__floor_panel_key:
			return (self.__floor_panel_up[:],self.__floor_panel_down[:])		
	
	def clear_floor_panel(self,orders_up,orders_down):
		with self.__floor_panel_key:
			for floor in range (0,N_FLOORS):			
				if (orders_up[floor] != 0):
					self.__floor_panel_up[floor] = 0
				if (orders_down[floor] != 0):
					self.__floor_panel_down[floor] = 0


	def read_position(self):
		return self.__position


	def __start(self):
		###### STARTS THE INITIAL-FUNCTIONS AND THREADS ######
		try:
			with watchdogs.WatchdogTimer(11):
				with self.__assigned_orders_key:
					self.__startup()
					self.__load_elevator_queue()
					self.__thread_run_elevator.daemon = True
					self.__thread_run_elevator.start()
					self.__thread_build_queues.daemon = True
					self.__thread_build_queues.start()
					self.__thread_set_indicators.daemon = True
					self.__thread_set_indicators.start()
		except watchdogs.WatchdogTimer:
			print "watchdog error"
			print "SlaveDriver.__start"
			interrupt_main()
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


	def __load_elevator_queue(self):
		###### READS OLD MASTER ORDERS FROM FILE ######
		try:
			with open("master_file_1", "rb") as master_file:
				(self.__assigned_orders_up, self.__assigned_orders_down) = pickle.load(master_file)
				self.__saved_assigned_orders_up = self.__assigned_orders_up[:]
				self.__saved_assigned_orders_down = self.__assigned_orders_down[:]
		except StandardError as error:
			print error
			print "SlaveDriver.__load_elevator_queue"
			print "master_file_1"
			try:
				with open("master_file_2", "rb") as master_file:
					(self.__assigned_orders_up, self.__assigned_orders_down) = pickle.load(master_file)
					self.__saved_assigned_orders_up = self.__assigned_orders_up[:]
					self.__saved_assigned_orders_down = self.__assigned_orders_down[:]
			except StandardError as error:
				print error
				print "SlaveDriver.__load_elevator_queue"
				print "master_file_2"

		###### ASSIGNES OLD MASTER ORDERS TO ELEVATOR ######
		for floor in range(0,N_FLOORS):
			if self.__saved_assigned_orders_up[floor] == MY_ID:
				self.__elevator_orders[floor][BUTTON_UP] = 1
			if self.__saved_assigned_orders_down[floor] == MY_ID:
				self.__elevator_orders[floor][BUTTON_DOWN] = 1

		###### READS OLD INTERNAL ORDERS FROM FILE ######
		try:
			with open("internal_file_1", "rb") as internal_file:
				self.__internal_orders = pickle.load(internal_file)
				self.__saved_internal_orders = self.__internal_orders[:]
		except StandardError as error:
			print error
			print "SlaveDriver.__load_elevator_queue"
			print "internal_file_1"
			try:
				with open("internal_file_2", "rb") as internal_file:
					self.__internal_orders = pickle.load(internal_file)
					self.__saved_internal_orders = self.__internal_orders[:]
			except StandardError as error:
				print error
				print "SlaveDriver.__load_elevator_queue"
				print "internal_file_2"

		###### ASSIGNS OLD INTERNAL ORDERS TO ELEVATOR ######
		for floor in range(0,N_FLOORS):
			self.__elevator_orders[floor][BUTTON_INTERNAL] = self.__saved_internal_orders[floor]


	def __run_elevator(self):
		##### RUNS THE ELEVATOR ACCORDING TO ASSIGNED ELEVATOR ORDERS ######
		try:
			__run_elevator_watchdog = watchdogs.ThreadWatchdog(2,"watchdog event: SlaveDriver.__run_elevator")
			__run_elevator_watchdog.StartWatchdog()

			last_floor = 0
			next_floor = 0
			next_button = 0
			direction = DIRN_STOP
			last_read_floor = -1

			while True:
				time.sleep(0.01)
				__run_elevator_watchdog.PetWatchdog()

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

				###### SETS DIRECTION TO STOP WHEN ELEVATOR REACHES HIGHEST/LOWEST ASSIGNED ELEVATOR ORDER ######
				if (direction == DIRN_UP) and (elevator_orders_max <= last_floor):
					direction = DIRN_STOP
				elif (direction == DIRN_DOWN) and (elevator_orders_min >= last_floor):
					direction = DIRN_STOP

				###### STOPS ELEVATOR AND CLEARS THE ELEVATOR ORDER LOCALLY ######
				if last_floor == next_floor:	
					self.__elevator_interface.set_motor_direction(DIRN_STOP)
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
					self.__position = (last_floor,next_floor,direction)
					time.sleep(1)
					move_timeout = time.time() + 4

				###### RUNS ELEVATOR IN UPWARD DIRECTION ######
				elif last_floor < next_floor:
					self.__elevator_interface.set_motor_direction(DIRN_UP)
					direction = DIRN_UP
					self.__position = (last_floor,next_floor,direction)

					###### CHECKS IF ELEVATOR IS MOVING ######
					if read_floor != last_read_floor:
						move_timeout = time.time() + 4
						last_read_floor = read_floor
					assert move_timeout > time.time(), "unknown error: elevator not moving"

				###### RUNS ELEVATOR IN DOWNWARD DIRECTION ######
				elif last_floor > next_floor:
					self.__elevator_interface.set_motor_direction(DIRN_DOWN)
					direction = DIRN_DOWN
					self.__position = (last_floor,next_floor,direction)

					###### CHECKS IF ELEVATOR IS MOVING ######
					if read_floor != last_read_floor:
						move_timeout = time.time() + 4
						last_read_floor = read_floor
					assert move_timeout > time.time(), "unknown error: elevator not moving"
			
				#print " my_id:" + str(MY_ID) + " up:" + str(self.__saved_assigned_orders_up) + " saved_up:" + str(self.__assigned_orders_up) + " down:" + str(self.__saved_assigned_orders_down) + " saved_down" + str(self.__assigned_orders_down) + " internal" + str(self.__internal_orders) + " saved_internal" + str(self.__saved_internal_orders) + " orders:" + str(self.__elevator_orders) + " n:" + str(next_floor) + " l:" + str(last_floor)

		except StandardError as error:
			print error
			print "SlaveDriver.__run_elevator"
			interrupt_main()


	def __build_queues(self):
		try:
			__build_queues_watchdog = watchdogs.ThreadWatchdog(1,"watchdog event: SlaveDriver.__build_queues")
			__build_queues_watchdog.StartWatchdog()

			while True:
				time.sleep(0.01)
				__build_queues_watchdog.PetWatchdog()

				for floor in range (0,N_FLOORS):
					for button in range(0,3):
						if (floor == 0 and button == BUTTON_DOWN) or (floor == N_FLOORS-1 and button == BUTTON_UP):
							pass
						elif self.__panel_interface.get_button_signal(button,floor):
							if button == BUTTON_INTERNAL:
								self.__internal_orders[floor]=1
							elif button == BUTTON_UP:
								with self.__floor_panel_key:
									self.__floor_panel_up[floor]=1
							elif button == BUTTON_DOWN:
								with self.__floor_panel_key:
									self.__floor_panel_down[floor]=1

					with self.__internal_orders_key:
						if self.__internal_orders != self.__saved_internal_orders:
							with open("internal_file_1", "wb") as internal_file:
								pickle.dump(self.__internal_orders, internal_file)

							with open("internal_file_2", "wb") as internal_file: 
								pickle.dump(self.__internal_orders, internal_file)
							try:
								with open("internal_file_1", "rb") as internal_file:
									self.__saved_internal_orders = pickle.load(internal_file)
								assert self.__internal_orders == self.__saved_internal_orders, "unknown error: loading internal_file_1"
							except StandardError as error:
								print error
								with open("internal_file_2", "rb") as internal_file: 
									self.__saved_internal_orders = pickle.load(internal_file)
								assert self.__internal_orders == self.__saved_internal_orders, "unknown error: loading internal_file_2"
							with self.__elevator_orders_key:
								if self.__saved_internal_orders[floor] == 1:
									self.__elevator_orders[floor][BUTTON_INTERNAL] = 1
						with self.__elevator_orders_key:
							if self.__elevator_orders[floor][BUTTON_INTERNAL] == 0:
								self.__internal_orders[floor] = 0
								
				with self.__assigned_orders_key:
					if (self.__assigned_orders_up != self.__saved_assigned_orders_up) or (self.__assigned_orders_down != self.__saved_assigned_orders_down):
						with open("master_file_1", "wb") as master_file:
							pickle.dump((self.__assigned_orders_up, self.__assigned_orders_down), master_file)

						with open("master_file_2", "wb") as master_file: 
							pickle.dump((self.__assigned_orders_up, self.__assigned_orders_down), master_file)

						try:
							with open("master_file_1", "rb") as master_file:
								(self.__saved_assigned_orders_up, self.__saved_assigned_orders_down) = pickle.load(master_file)
							assert self.__assigned_orders_up == self.__saved_assigned_orders_up, "unknown error: loading master_file_1"
							assert self.__assigned_orders_down == self.__saved_assigned_orders_down, "unknown error: loading master_file_1"
						except StandardError as error:
							print error
							with open("master_file_2", "rb") as master_file: 
									(self.__saved_assigned_orders_up, self.__saved_assigned_orders_down) = pickle.load(master_file)
							assert self.__assigned_orders_up == self.__saved_assigned_orders_up, "unknown error: loading master_file_2"
							assert self.__assigned_orders_down == self.__saved_assigned_orders_down, "unknown error: loading master_file_2"

						with self.__elevator_orders_key:
							for floor in range(0,N_FLOORS):
							# UP calls	
								if self.__saved_assigned_orders_up[floor] == MY_ID:
									self.__elevator_orders[floor][BUTTON_UP]=1
								else: 
									self.__elevator_orders[floor][BUTTON_UP]=0 # increases efficiency, might remove orders if bugged, testing ongoing
							# DOWN calls
								if self.__saved_assigned_orders_down[floor] == MY_ID:
									self.__elevator_orders[floor][BUTTON_DOWN]=1
								else: 
									self.__elevator_orders[floor][BUTTON_DOWN]=0 # increases efficiency, might remove orders if bugged, testing ongoing
				
				
				#print self.__master_queue
				#print self.__saved_master_queue


		except StandardError as error:
			print error
			print "SlaveDriver.__build_queues"
			interrupt_main()


	def __set_indicators(self):
		try:
			__set_indicators_watchdog = watchdogs.ThreadWatchdog(1,"watchdog event: SlaveDriver.__set_indicators_watchdog")
			__set_indicators_watchdog.StartWatchdog()

			while True:
				time.sleep(0.01)
				__set_indicators_watchdog.PetWatchdog()

				###### CALL INDICATORS #####
				with self.__assigned_orders_key:
					for floor in range(0,N_FLOORS):
					# UP calls
						if floor != 3:
							if self.__saved_assigned_orders_up[floor] > 0:
								self.__panel_interface.set_button_lamp(BUTTON_UP,floor,1)
							else:
								self.__panel_interface.set_button_lamp(BUTTON_UP,floor,0)
					# DOWN calls
						if floor != 0:
							if self.__saved_assigned_orders_down[floor] > 0:
								self.__panel_interface.set_button_lamp(BUTTON_DOWN,floor,1)
							else:
								self.__panel_interface.set_button_lamp(BUTTON_DOWN,floor,0)
					# Internal calls
						with self.__internal_orders_key:
							if self.__saved_internal_orders[floor] == 1:
								self.__panel_interface.set_button_lamp(BUTTON_INTERNAL,floor,1)
							else:
								self.__panel_interface.set_button_lamp(BUTTON_INTERNAL,floor,0)
																	
				###### GET POSITION ######
				(last_floor, next_floor, direction) = self.__position
				
				###### OPEN DOOR INDICATOR ######
				if last_floor == next_floor:
					self.__panel_interface.set_door_open_lamp(1)
				else:
					self.__panel_interface.set_door_open_lamp(0)

				###### FLOOR INDICATOR ######
				self.__panel_interface.set_floor_indicator(last_floor)

		except StandardError as error:
			print error
			print "SlaveDriver.__set_indicators"
			interrupt_main()

