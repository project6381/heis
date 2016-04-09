from ported_drivers.elevator_interface import ElevatorInterface
from ported_drivers.panel_interface import PanelInterface
from ported_drivers.constants import DIRN_STOP, DIRN_UP, DIRN_DOWN, BUTTON_CALL_UP, BUTTON_CALL_DOWN, BUTTON_COMMAND, N_FLOORS
from config_parameters import MY_ID
from threading import Thread, Lock
from thread import interrupt_main
import time
import pickle
import watchdogs


class SlaveDriver:
	def __init__(self):
		self.__elevator_interface = ElevatorInterface()
		self.__panel_interface = PanelInterface()
		self.__elevator_queue_key = Lock()
		self.__master_queue_key = Lock()
		self.__internal_queue_key = Lock()
		self.__floor_panel_key = Lock()
		self.__elevator_queue = [[0 for button in range(0,3)] for floor in range(0,N_FLOORS)]
		self.__master_queue = [0]*N_FLOORS*2
		self.__saved_master_queue = [0]*N_FLOORS*2
		self.__internal_queue = [0]*N_FLOORS
		self.__saved_internal_queue = [0]*N_FLOORS
		self.__floor_panel_up = [0]*4
		self.__floor_panel_down = [0]*4
		self.__last_master_id = 0
		self.__position = (0,0,DIRN_STOP)
		self.__thread_run_elevator = Thread(target = self.__run_elevator, args = (),)
		self.__thread_build_queues = Thread(target = self.__build_queues, args = (),)
		self.__thread_set_indicators = Thread(target = self.__set_indicators, args = (),)
		self.__start()



	
	def changing_master(self,master_id):
		with watchdogs.WatchdogTimer(1):
			if self.__last_master_id !=  master_id:
				self.__last_master_id = master_id
				return True
			else: 
				return False


	def master_queue_elevator_run(self,master_queue):
		with watchdogs.WatchdogTimer(1):
			time.sleep(0.01)
			with self.__master_queue_key:
				self.__master_queue = master_queue[:]

	def read_saved_master_queue(self):
		with watchdogs.WatchdogTimer(1):
			time.sleep(0.01)
			with self.__master_queue_key:
				return self.__saved_master_queue
	
	def get_floor_panel(self):
		with watchdogs.WatchdogTimer(1):
			with self.__floor_panel_key:
				return (self.__floor_panel_up[:],self.__floor_panel_down[:])		
	
	def clear_floor_panel(self,orders_up,orders_down):
		with watchdogs.WatchdogTimer(1):
			with self.__floor_panel_key:
				for i in range (0,N_FLOORS):			
					if (orders_up[i] != 0):
						self.__floor_panel_up[i] = 0
					if (orders_down[i] != 0):
						self.__floor_panel_down[i] = 0


	def read_position(self):
		with watchdogs.WatchdogTimer(1):
			return self.__position


	def __start(self):
		with self.__master_queue_key:
			try:
				with watchdogs.WatchdogTimer(10):
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
		try:
			check_floor = self.__elevator_interface.get_floor_sensor_signal()
			turn_time = time.time() + 5
			reset_time = time.time() + 10

			while check_floor < 0:
				if turn_time > time.time():
					self.__elevator_interface.set_motor_direction(DIRN_DOWN)
					pass
				else:
					self.__elevator_interface.set_motor_direction(DIRN_UP)
					if reset_time < time.time():
						turn_time = time.time() + 5
						reset_time = time.time() + 10
				check_floor = self.__elevator_interface.get_floor_sensor_signal()
		
			self.__elevator_interface.set_motor_direction(DIRN_STOP)

		except StandardError as error:
			print error
			print "SlaveDriver.__startup"
			interrupt_main()


	def __load_elevator_queue(self):
		try:
			with open("master_file_1", "rb") as master_file:
				self.__master_queue = pickle.load(master_file)
				self.__saved_master_queue = self.__master_queue[:]
		except StandardError as error:
			print error
			print "SlaveDriver.__load_elevator_queue"
			print "master_file_1"
			try:
				with open("master_file_2", "rb") as master_file:
					self.__master_queue = pickle.load(master_file)
					self.__saved_master_queue = self.__master_queue[:]
			except StandardError as error:
				print error
				print "SlaveDriver.__load_elevator_queue"
				print "master_file_2"

		for floor in range(0,N_FLOORS):
			if self.__saved_master_queue[floor] == MY_ID:
				self.__elevator_queue[floor][BUTTON_CALL_UP] = 1
		for floor in range(N_FLOORS,N_FLOORS*2):
			if self.__saved_master_queue[floor] == MY_ID:
				self.__elevator_queue[floor-N_FLOORS][BUTTON_CALL_DOWN] = 1

		try:
			with open("internal_file_1", "rb") as internal_file:
				self.__internal_queue = pickle.load(internal_file)
				self.__saved_internal_queue = self.__internal_queue[:]
		except StandardError as error:
			print error
			print "SlaveDriver.__load_elevator_queue"
			print "internal_file_1"
			try:
				with open("internal_file_2", "rb") as internal_file:
					self.__internal_queue = pickle.load(internal_file)
					self.__saved_internal_queue = self.__internal_queue[:]
			except StandardError as error:
				print error
				print "SlaveDriver.__load_elevator_queue"
				print "internal_file_2"

		for floor in range(0,N_FLOORS):
			self.__elevator_queue[floor][BUTTON_COMMAND] = self.__saved_internal_queue[floor]


	def __run_elevator(self):
		try:
			__run_elevator_watchdog = watchdogs.ThreadWatchdog(2,"watchdog event: SlaveDriver.__run_elevator")
			__run_elevator_watchdog.StartWatchdog()

			last_floor = 0
			next_floor = 0
			next_button = 0
			direction = DIRN_STOP

			while True:
				time.sleep(0.01)
				__run_elevator_watchdog.PetWatchdog()
				#print self.__elevator_queue
				floor_max = 0
				floor_min = N_FLOORS-1

				with self.__elevator_queue_key:
					for floor in range(0,N_FLOORS):
						for button in range(0,3):
								if self.__elevator_queue[floor][button] == 1:
									floor_max = max(floor_max,floor)
									floor_min = min(floor_min,floor)
									if (last_floor == next_floor) and (direction != DIRN_DOWN) and (next_floor <= floor_max):
										next_floor = floor
										next_button = button
									elif (last_floor == next_floor) and (direction != DIRN_UP) and (next_floor >= floor_min):
										next_floor = floor
										next_button = button
									elif (last_floor < next_floor) and (floor < next_floor) and (floor > last_floor) and (button != BUTTON_CALL_DOWN):
										next_floor = floor
										next_button = button
									elif (last_floor > next_floor) and (floor > next_floor) and (floor < last_floor) and (button != BUTTON_CALL_UP):
										next_floor = floor
										next_button = button
				
				if (direction == DIRN_UP) and (floor_max > 0) and (next_button == BUTTON_CALL_DOWN):
					next_floor = floor_max
				elif (direction == DIRN_DOWN) and (floor_min < N_FLOORS-1) and (next_button == BUTTON_CALL_UP):
					next_floor = floor_min

				read_floor = self.__elevator_interface.get_floor_sensor_signal()
				if read_floor >= 0:
					last_floor = read_floor

				if (direction == DIRN_UP) and (floor_max <= last_floor):
					direction = DIRN_STOP
				elif (direction == DIRN_DOWN) and (floor_min >= last_floor):
					direction = DIRN_STOP

				if last_floor == next_floor:
					self.__elevator_interface.set_motor_direction(DIRN_STOP)
					if direction == DIRN_STOP:
						with self.__elevator_queue_key:
							self.__elevator_queue[next_floor][0] = 0
							self.__elevator_queue[next_floor][1] = 0
							self.__elevator_queue[next_floor][2] = 0
					elif direction == DIRN_UP:
						with self.__elevator_queue_key:
							self.__elevator_queue[next_floor][0] = 0
							self.__elevator_queue[next_floor][2] = 0
					elif direction == DIRN_DOWN:
						with self.__elevator_queue_key:
							self.__elevator_queue[next_floor][1] = 0
							self.__elevator_queue[next_floor][2] = 0
					self.__position = (last_floor,next_floor,direction)
					time.sleep(1)
				elif last_floor < next_floor:
					self.__elevator_interface.set_motor_direction(DIRN_UP)
					direction = DIRN_UP
					self.__position = (last_floor,next_floor,direction)
				elif last_floor > next_floor:
					self.__elevator_interface.set_motor_direction(DIRN_DOWN)
					direction = DIRN_DOWN
					self.__position = (last_floor,next_floor,direction)

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
						if (floor == 0 and button == BUTTON_CALL_DOWN) or (floor == 3 and button == BUTTON_CALL_UP):
							pass
						elif self.__panel_interface.get_button_signal(button,floor):
							if button == BUTTON_COMMAND:
								self.__internal_queue[floor]=1
							elif button == 0:
								with self.__floor_panel_key:
									self.__floor_panel_up[floor]=1
							elif button == 1:
								with self.__floor_panel_key:
									self.__floor_panel_down[floor]=1

					with self.__internal_queue_key:
						if self.__internal_queue != self.__saved_internal_queue:
							with open("internal_file_1", "wb") as internal_file:
								pickle.dump(self.__internal_queue, internal_file)

							with open("internal_file_2", "wb") as internal_file: 
								pickle.dump(self.__internal_queue, internal_file)
							try:
								with open("internal_file_1", "rb") as internal_file:
									self.__saved_internal_queue = pickle.load(internal_file)
								assert self.__internal_queue == self.__saved_internal_queue, "unknown error loading internal_file_1"
							except StandardError as error:
								print error
								with open("internal_file_2", "rb") as internal_file: 
									self.__saved_internal_queue = pickle.load(internal_file)
								assert self.__internal_queue == self.__saved_internal_queue, "unknown error loading internal_file_2"
							with self.__elevator_queue_key:
								if self.__saved_internal_queue[floor] == 1:
									self.__elevator_queue[floor][button] = 1
						with self.__elevator_queue_key:
							if self.__elevator_queue[floor][BUTTON_COMMAND] == 0:
								self.__internal_queue[floor] = 0
								
				with self.__master_queue_key:
					if self.__master_queue != self.__saved_master_queue:
						with open("master_file_1", "wb") as master_file:
							pickle.dump(self.__master_queue, master_file)

						with open("master_file_2", "wb") as master_file: 
							pickle.dump(self.__master_queue, master_file)

						try:
							with open("master_file_1", "rb") as master_file:
								self.__saved_master_queue = pickle.load(master_file)
							assert self.__master_queue == self.__saved_master_queue, "unknown error loading master_file_1"
						except StandardError as error:
							print error
							with open("master_file_2", "rb") as master_file: 
								self.__saved_master_queue = pickle.load(master_file)
							assert self.__master_queue == self.__saved_master_queue, "unknown error loading master_file_2"

						with self.__elevator_queue_key:
							for floor in range(0,N_FLOORS):
								if self.__saved_master_queue[floor] == MY_ID:
									self.__elevator_queue[floor][BUTTON_CALL_UP]=1
								#else: 
								#	self.__elevator_queue[floor][BUTTON_CALL_UP]=0
							for floor in range(N_FLOORS,N_FLOORS*2):
								if self.__saved_master_queue[floor] == MY_ID:
									self.__elevator_queue[floor-N_FLOORS][BUTTON_CALL_DOWN]=1
								#else: 
								#	self.__elevator_queue[floor-N_FLOORS][BUTTON_CALL_DOWN]=0
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
				
				with self.__master_queue_key:
					for floor in range(0,N_FLOORS):
						if floor != 3:
							if self.__saved_master_queue[floor] > 0:
								self.__panel_interface.set_button_lamp(BUTTON_CALL_UP,floor,1)
							else:
								self.__panel_interface.set_button_lamp(BUTTON_CALL_UP,floor,0)
					for floor in range(N_FLOORS,N_FLOORS*2):
						if floor != 0:
							if self.__saved_master_queue[floor] > 0:
								self.__panel_interface.set_button_lamp(BUTTON_CALL_DOWN,floor-N_FLOORS,1)
							else:
								self.__panel_interface.set_button_lamp(BUTTON_CALL_DOWN,floor-N_FLOORS,0)

				with self.__internal_queue_key:
					for floor in range(0,N_FLOORS):
						if self.__saved_internal_queue[floor] == 1:
							self.__panel_interface.set_button_lamp(BUTTON_COMMAND,floor,1)
						else:
							self.__panel_interface.set_button_lamp(BUTTON_COMMAND,floor,0)
																	
				
				(last_floor, next_floor, direction) = self.__position
				
				if last_floor == next_floor:
					self.__panel_interface.set_door_open_lamp(1)
				else:
					self.__panel_interface.set_door_open_lamp(0)

				self.__panel_interface.set_floor_indicator(last_floor)

		except StandardError as error:
			print error
			print "SlaveDriver.__set_indicators"
			interrupt_main()

