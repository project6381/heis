import pickle
import time
from thread import interrupt_main
from threading import Thread, Lock

import watchdogs
from config_parameters import MY_ID, TICK, MOVE_TIMEOUT
from ported_driver.constants import DIRN_STOP, DIRN_UP, DIRN_DOWN, BUTTON_UP, BUTTON_DOWN, BUTTON_INTERNAL, N_FLOORS, \
    N_BUTTONS
from ported_driver.elevator_interface import ElevatorInterface
from ported_driver.panel_interface import PanelInterface


class SlaveHandler(object):
    def __init__(self):
        self.__elevator_interface = ElevatorInterface()
        self.__panel_interface = PanelInterface()

        self.__elevator_orders = [[0 for button in range(0, N_BUTTONS)] for floor in range(0, N_FLOORS)]
        self.__master_orders_up = [0 for floor in range(0, N_FLOORS)]
        self.__master_orders_down = [0 for floor in range(0, N_FLOORS)]
        self.__saved_master_orders_up = [0 for floor in range(0, N_FLOORS)]
        self.__saved_master_orders_down = [0 for floor in range(0, N_FLOORS)]
        self.__internal_orders = [0 for floor in range(0, N_FLOORS)]
        self.__saved_internal_orders = [0 for floor in range(0, N_FLOORS)]
        self.__external_buttons_up = [0 for floor in range(0, N_FLOORS)]
        self.__external_buttons_down = [0 for floor in range(0, N_FLOORS)]

        self.__elevator_orders_key = Lock()
        self.__master_orders_key = Lock()
        self.__internal_orders_key = Lock()
        self.__external_buttons_key = Lock()
        self.__position_key = Lock()
        self.__offline_mode_key = Lock()
        self.__movement_timed_out_key = Lock()

        self.__last_master_id = 0
        self.__position = (0, 0, DIRN_STOP)

        self.__movement_timed_out = False
        self.__offline_mode = False
        self.__changing_master = False

        self.__thread_run_elevator = Thread(target=self.__run_elevator_thread, args=(),
                                            name="SlaveHandler.__run_elevator_thread")
        self.__thread_read_button = Thread(target=self.__read_buttons_thread, args=(),
                                           name="SlaveHandler.__thread_read_button")
        self.__thread_set_indicators = Thread(target=self.__indicators_thread, args=(),
                                              name="SlaveHandler.__thread_set_indicators")
        self.__thread_save_orders = Thread(target=self.__process_orders_thread, args=(),
                                           name="SlaveHandler.__thread_save_orders")

        self.__init_startup_sequence()

    def changing_master(self, master_message):
        if self.__last_master_id != master_message['master_id']:
            self.__last_master_id = master_message['master_id']
            self.__changing_master = True
            return True

        if self.__changing_master:

            ###### 'CHANGING MASTER' UNTIL 'MASTER ORDERS' CONTAINS ALL 'UNFINISHED ORDERS' ######
            (unfinished_orders_up, unfinished_orders_down) = self.unfinished_orders()
            for floor in range(0, N_FLOORS):
                if ((unfinished_orders_up[floor] > 0) and (master_message['orders_up'][floor] == 0)) or (
                            (unfinished_orders_down[floor] > 0) and (master_message['orders_down'][floor] == 0)):
                    self.__changing_master = True
                    return True

        self.__changing_master = False
        return False

    def update_master_orders(self, master_order_up, master_order_down):
        with self.__master_orders_key:
            self.__master_orders_up = master_order_up
            self.__master_orders_down = master_order_down

    def unfinished_orders(self):
        with self.__master_orders_key:
            unfinished_orders_up = self.__saved_master_orders_up[:]
            unfinished_orders_down = self.__saved_master_orders_down[:]

        ###### REMOVE ASSIGNMENT FROM ORDERS ######
        for floor in range(0, N_FLOORS):
            if unfinished_orders_up[floor] > 0:
                unfinished_orders_up[floor] = 1

            if unfinished_orders_down[floor] > 0:
                unfinished_orders_down[floor] = 1

        return unfinished_orders_up[:], unfinished_orders_down[:]

    def external_buttons_pressed(self):
        with self.__external_buttons_key:
            return self.__external_buttons_up[:], self.__external_buttons_down[:]

    def read_position(self):
        with self.__position_key:
            return self.__position

    def set_offline_mode(self, offline_mode):
        with self.__offline_mode_key:
            self.__offline_mode = offline_mode

    def movement_timeout(self):
        with self.__movement_timed_out_key:
            if self.__movement_timed_out:
                return True
            else:
                return False

    def __init_startup_sequence(self):
        try:
            with self.__master_orders_key:
                self.__find_a_floor()
                self.__load_elevator_orders_from_file()
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
            print "SlaveHandler.__init_startup_sequence"
            interrupt_main()

    def __find_a_floor(self):
        try:
            check_floor = self.__elevator_interface.get_floor_sensor_signal()
            turn_time = time.time() + 5
            timeout_time = time.time() + 10

            while check_floor < 0:
                if turn_time > time.time():
                    self.__elevator_interface.set_motor_direction(DIRN_DOWN)
                else:
                    self.__elevator_interface.set_motor_direction(DIRN_UP)
                check_floor = self.__elevator_interface.get_floor_sensor_signal()
                assert timeout_time > time.time(), "unknown error: elevator not moving?"

            self.__elevator_interface.set_motor_direction(DIRN_STOP)

        except StandardError as error:
            print error
            print "SlaveHandler.__find_a_floor"
            interrupt_main()

    def __load_elevator_orders_from_file(self):
        ###### TRY TO OPEN MASTER ORDERS FILE, IF IT FAILES TRY THE BACKUP ######
        try:
            with open("master_file_main", "rb") as master_file:
                (self.__master_orders_up, self.__master_orders_down) = pickle.load(master_file)
                self.__saved_master_orders_up = self.__master_orders_up[:]
                self.__saved_master_orders_down = self.__master_orders_down[:]

        except StandardError as error:
            print error
            print "SlaveHandler.__load_elevator_orders_from_file"
            print "master_file_main"

            try:
                with open("master_file_backup", "rb") as master_file:
                    (self.__master_orders_up, self.__master_orders_down) = pickle.load(master_file)
                    self.__saved_master_orders_up = self.__master_orders_up[:]
                    self.__saved_master_orders_down = self.__master_orders_down[:]

            except StandardError as error:
                print error
                print "SlaveHandler.__load_elevator_orders_from_file"
                print "master_file_backup"

        ###### ASSIGNS OLD MASTER ORDERS TO ELEVATOR ORDERS ######
        for floor in range(0, N_FLOORS):
            if self.__saved_master_orders_up[floor] == MY_ID:
                self.__elevator_orders[floor][BUTTON_UP] = 1
            if self.__saved_master_orders_down[floor] == MY_ID:
                self.__elevator_orders[floor][BUTTON_DOWN] = 1

        ###### TRY TO OPEN INTERNAL ORDERS FILE, IF IT FAILES TRY THE BACKUP ######
        try:
            with open("internal_file_main", "rb") as internal_file:
                self.__internal_orders = pickle.load(internal_file)
                self.__saved_internal_orders = self.__internal_orders[:]

        except StandardError as error:
            print error
            print "SlaveHandler.__load_elevator_orders_from_file"
            print "internal_file_main"

            try:
                with open("internal_file_backup", "rb") as internal_file:
                    self.__internal_orders = pickle.load(internal_file)
                    self.__saved_internal_orders = self.__internal_orders[:]

            except StandardError as error:
                print error
                print "SlaveHandler.__load_elevator_orders_from_file"
                print "internal_file_backup"

        ###### ASSIGNS OLD INTERNAL ORDERS TO ELEVATOR ORDERS ######
        for floor in range(0, N_FLOORS):
            self.__elevator_orders[floor][BUTTON_INTERNAL] = self.__saved_internal_orders[floor]

    def __run_elevator_thread(self):
        try:
            __run_elevator_thread_watchdog = watchdogs.ThreadWatchdog(5, "Watchdog: __run_elevator_thread")
            __run_elevator_thread_watchdog.start_watchdog()

            last_floor = 0
            next_floor = 0
            next_button = 0
            last_direction = DIRN_STOP
            direction = DIRN_STOP
            last_read_floor = -1

            while True:
                time.sleep(TICK)
                __run_elevator_thread_watchdog.pet_watchdog()

                ###### DECIDES WHICH FLOOR TO GO TO NEXT ######
                highest_elevator_order = 0
                lowest_elevator_order = N_FLOORS - 1
                with self.__elevator_orders_key:
                    for floor in range(0, N_FLOORS):
                        for button in range(0, N_BUTTONS):
                            if self.__elevator_orders[floor][button] == 1:
                                highest_elevator_order = max(highest_elevator_order, floor)
                                lowest_elevator_order = min(lowest_elevator_order, floor)
                                if (last_floor == next_floor) and (direction != DIRN_DOWN) and (
                                            next_floor <= highest_elevator_order):
                                    next_floor = floor
                                    next_button = button
                                elif (last_floor == next_floor) and (direction != DIRN_UP) and (
                                            next_floor >= lowest_elevator_order):
                                    next_floor = floor
                                    next_button = button
                                elif (last_floor < next_floor) and (floor < next_floor) and (floor > last_floor) and (
                                            button != BUTTON_DOWN):
                                    next_floor = floor
                                    next_button = button
                                elif (last_floor > next_floor) and (floor > next_floor) and (floor < last_floor) and (
                                            button != BUTTON_UP):
                                    next_floor = floor
                                    next_button = button
                if (direction == DIRN_UP) and (highest_elevator_order > 0) and (next_button == BUTTON_DOWN):
                    next_floor = highest_elevator_order
                elif (direction == DIRN_DOWN) and (lowest_elevator_order < N_FLOORS - 1) and (next_button == BUTTON_UP):
                    next_floor = lowest_elevator_order

                read_floor = self.__elevator_interface.get_floor_sensor_signal()
                if read_floor >= 0:
                    last_floor = read_floor

                if (direction == DIRN_UP) and (highest_elevator_order <= last_floor):
                    last_direction = direction
                    direction = DIRN_STOP
                elif (direction == DIRN_DOWN) and (lowest_elevator_order >= last_floor):
                    last_direction = direction
                    direction = DIRN_STOP

                ###### ELEVATOR ARRIVED AT FLOOR ######
                if last_floor == next_floor:

                    self.__elevator_interface.set_motor_direction(DIRN_STOP)

                    with self.__position_key:
                        self.__position = (last_floor, next_floor, direction)

                    ###### CHECKS THAT ELEVATOR ACTUALLY STOPPED ######
                    time.sleep(1)
                    read_floor = self.__elevator_interface.get_floor_sensor_signal()
                    if read_floor != last_floor:

                        ###### RUN ELEVATOR IN OPPOSITE DIRECTION ######
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
                            time.sleep(TICK)
                            read_floor = self.__elevator_interface.get_floor_sensor_signal()
                        self.__elevator_interface.set_motor_direction(DIRN_STOP)

                    ###### CLEAR COMPLETED ORDERS ######
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

                    time.sleep(1)

                    movement_timeout = time.time() + MOVE_TIMEOUT

                ###### ELEVATOR IS BELOW NEXT FLOOR ######
                elif last_floor < next_floor:

                    self.__elevator_interface.set_motor_direction(DIRN_UP)
                    direction = DIRN_UP

                    with self.__position_key:
                        self.__position = (last_floor, next_floor, direction)

                    ###### CHECKS THAT THE ELEVATOR IS MOVING ######
                    if read_floor != last_read_floor:
                        movement_timeout = time.time() + MOVE_TIMEOUT
                        last_read_floor = read_floor
                    with self.__movement_timed_out_key:
                        if movement_timeout < time.time():
                            self.__movement_timed_out = True
                        else:
                            self.__movement_timed_out = False

                ###### ELEVATOR IS ABOVE NEXT FLOOR ######
                elif last_floor > next_floor:

                    self.__elevator_interface.set_motor_direction(DIRN_DOWN)
                    direction = DIRN_DOWN

                    with self.__position_key:
                        self.__position = (last_floor, next_floor, direction)

                    ###### CHECKS THAT THE ELEVATOR IS MOVING ######
                    if read_floor != last_read_floor:
                        movement_timeout = time.time() + MOVE_TIMEOUT
                        last_read_floor = read_floor
                    with self.__movement_timed_out_key:
                        if movement_timeout < time.time():
                            self.__movement_timed_out = True
                        else:
                            self.__movement_timed_out = False

        except StandardError as error:
            print error
            print "SlaveHandler.__run_elevator_thread"
            interrupt_main()

    def __read_buttons_thread(self):
        try:
            __read_buttons_thread_watchdog = watchdogs.ThreadWatchdog(1, "Watchdog: __read_buttons_thread")
            __read_buttons_thread_watchdog.start_watchdog()

            while True:
                time.sleep(TICK)
                __read_buttons_thread_watchdog.pet_watchdog()

                for floor in range(0, N_FLOORS):
                    for button in range(0, N_BUTTONS):

                        ###### FILTERS NONEXISTING BUTTONS ######
                        if (floor == 0 and button == BUTTON_DOWN) or (floor == N_FLOORS - 1 and button == BUTTON_UP):
                            pass

                        ###### SET BUTTONS ######
                        elif self.__panel_interface.get_button_signal(button, floor):
                            if button == BUTTON_INTERNAL:
                                with self.__internal_orders_key:
                                    self.__internal_orders[floor] = 1
                            elif button == BUTTON_UP:
                                with self.__external_buttons_key:
                                    self.__external_buttons_up[floor] = 1
                            elif button == BUTTON_DOWN:
                                with self.__external_buttons_key:
                                    self.__external_buttons_down[floor] = 1

                        ###### CLEAR BUTTONS ######
                        else:
                            if button == BUTTON_UP:
                                with self.__external_buttons_key:
                                    self.__external_buttons_up[floor] = 0
                            elif button == BUTTON_DOWN:
                                with self.__external_buttons_key:
                                    self.__external_buttons_down[floor] = 0

        except StandardError as error:
            print error
            print "SlaveHandler.__read_buttons_thread"
            interrupt_main()

    def __process_orders_thread(self):
        try:
            __process_orders_thread_watchdog = watchdogs.ThreadWatchdog(1, "Watchdog: __process_orders_thread")
            __process_orders_thread_watchdog.start_watchdog()

            while True:
                time.sleep(TICK)
                __process_orders_thread_watchdog.pet_watchdog()

                ###### PROCESS INTERNAL ORDERS ######
                with self.__internal_orders_key:
                    if self.__internal_orders != self.__saved_internal_orders:

                        ###### SAVES INTERNAL ORDERS TO FILE WITH BACKUP ######
                        with open("internal_file_main", "wb") as internal_file:
                            pickle.dump(self.__internal_orders, internal_file)
                        with open("internal_file_backup", "wb") as internal_file:
                            pickle.dump(self.__internal_orders, internal_file)

                        ###### READ BACK AND COMPARE INTERNAL ORDERS ######
                        try:
                            with open("internal_file_main", "rb") as internal_file:
                                self.__saved_internal_orders = pickle.load(internal_file)
                            assert (self.__internal_orders == self.__saved_internal_orders,
                                    "unknown error: loading internal_file_main")
                        except StandardError as error:
                            print error
                            with open("internal_file_backup", "rb") as internal_file:
                                self.__saved_internal_orders = pickle.load(internal_file)
                            assert (self.__internal_orders == self.__saved_internal_orders,
                                    "unknown error: loading internal_file_backup")

                        ###### ADDS SAVED INTERNAL ORDERS TO ELEVATOR ORDERS ######
                        with self.__elevator_orders_key:
                            for floor in range(0, N_FLOORS):
                                if self.__saved_internal_orders[floor] == 1:
                                    self.__elevator_orders[floor][BUTTON_INTERNAL] = 1

                    ###### CLEARS COMPLETE ELEVATOR ORDERS FROM INTERNAL ORDERS ######
                    with self.__elevator_orders_key:
                        for floor in range(0, N_FLOORS):
                            if self.__elevator_orders[floor][BUTTON_INTERNAL] == 0:
                                self.__internal_orders[floor] = 0

                ###### PROCESS MASTER ORDERS ######
                with self.__master_orders_key:
                    if (self.__master_orders_up != self.__saved_master_orders_up) or (
                                self.__master_orders_down != self.__saved_master_orders_down):

                        ###### SAVES MASTER ORDERS UP/DOWN TO FILE WITH BACKUP ######
                        with open("master_file_main", "wb") as master_file:
                            pickle.dump((self.__master_orders_up, self.__master_orders_down), master_file)
                        with open("master_file_backup", "wb") as master_file:
                            pickle.dump((self.__master_orders_up, self.__master_orders_down), master_file)

                        ###### READ BACK AND COMPARE MASTER ORDERS ######
                        try:
                            with open("master_file_main", "rb") as master_file:
                                (self.__saved_master_orders_up, self.__saved_master_orders_down) = pickle.load(
                                    master_file)
                            assert (self.__master_orders_up == self.__saved_master_orders_up,
                                    "unknown error: loading master_file_main")
                            assert (self.__master_orders_down == self.__saved_master_orders_down,
                                    "unknown error: loading master_file_main")
                        except StandardError as error:
                            print error
                            with open("master_file_backup", "rb") as master_file:
                                (self.__saved_master_orders_up, self.__saved_master_orders_down) = pickle.load(
                                    master_file)
                            assert (self.__master_orders_up == self.__saved_master_orders_up,
                                    "unknown error: loading master_file_backup")
                            assert (self.__master_orders_down == self.__saved_master_orders_down,
                                    "unknown error: loading master_file_backup")

                        ###### ADDS SAVED MASTER ORDERS UP/DOWN WITH MY ID TO ELEVATOR ORDERS ######
                        with self.__elevator_orders_key:
                            for floor in range(0, N_FLOORS):
                                if self.__saved_master_orders_up[floor] == MY_ID:
                                    self.__elevator_orders[floor][BUTTON_UP] = 1
                                if self.__saved_master_orders_down[floor] == MY_ID:
                                    self.__elevator_orders[floor][BUTTON_DOWN] = 1

                    ###### OFFLINE MODE ######
                    with self.__offline_mode_key:
                        if self.__offline_mode:

                            ###### CHANGES ALL SAVED MASTER ORDERS TO MY ID ######
                            for floor in range(0, N_FLOORS):
                                if self.__saved_master_orders_up[floor] > 0:
                                    self.__master_orders_up[floor] = MY_ID
                                if self.__saved_master_orders_down[floor] > 0:
                                    self.__master_orders_down[floor] = MY_ID

                            ###### CLEARS COMPLETE ELEVATOR ORDERS UP/DOWN FROM MASTER ORDERS ######
                            with self.__elevator_orders_key:
                                for floor in range(0, N_FLOORS):
                                    if (self.__saved_master_orders_up[floor] == MY_ID) and (
                                                self.__elevator_orders[floor][BUTTON_UP] == 0):
                                        self.__master_orders_up[floor] = 0
                                    if (self.__saved_master_orders_down[floor] == MY_ID) and (
                                                self.__elevator_orders[floor][BUTTON_DOWN] == 0):
                                        self.__master_orders_down[floor] = 0

        except StandardError as error:
            print error
            print "SlaveHandler.__process_orders_thread"
            interrupt_main()

    def __indicators_thread(self):
        try:
            __indicators_thread_watchdog = watchdogs.ThreadWatchdog(1, "Watchdog: __indicators_thread_watchdog")
            __indicators_thread_watchdog.start_watchdog()

            while True:
                time.sleep(TICK)
                __indicators_thread_watchdog.pet_watchdog()

                ###### SETS CALL INDICATORS #####
                with self.__master_orders_key:
                    for floor in range(0, N_FLOORS):

                        ###### UP CALLS ######
                        if floor != (N_FLOORS - 1):
                            if self.__saved_master_orders_up[floor] > 0:
                                self.__panel_interface.set_button_lamp(BUTTON_UP, floor, 1)
                            else:
                                self.__panel_interface.set_button_lamp(BUTTON_UP, floor, 0)

                        ###### DOWN CALLS ######
                        if floor != 0:
                            if self.__saved_master_orders_down[floor] > 0:
                                self.__panel_interface.set_button_lamp(BUTTON_DOWN, floor, 1)
                            else:
                                self.__panel_interface.set_button_lamp(BUTTON_DOWN, floor, 0)

                        ###### INTERNAL CALLS ######
                        with self.__internal_orders_key:
                            if self.__saved_internal_orders[floor] == 1:
                                self.__panel_interface.set_button_lamp(BUTTON_INTERNAL, floor, 1)
                            else:
                                self.__panel_interface.set_button_lamp(BUTTON_INTERNAL, floor, 0)

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
            print "SlaveHandler.__indicators_thread"
            interrupt_main()
