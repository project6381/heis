import time
from socket import socket, AF_INET, SOCK_DGRAM, SOL_SOCKET, SO_BROADCAST
from thread import interrupt_main
from threading import Thread, Lock

import watchdogs
from config_parameters import MASTER_TO_SLAVE_PORT, SLAVE_TO_MASTER_PORT, TICK
from ported_driver.constants import N_FLOORS


class MessageHandler:
    def __init__(self):
        self.__receive_buffer_slave = []
        self.__receive_buffer_master = []

        self.__receive_buffer_slave_key = Lock()
        self.__receive_buffer_master_key = Lock()
        self.__is_connected_to_network_key = Lock()
        self.__no_active_master_key = Lock()

        self.__no_active_master = False
        self.__master_thread_started = False
        self.__slave_thread_started = False
        self.__master_alive_thread_started = False
        self.__is_connected_to_network = False

        self.__slave_message = {'buttons_up': [0 for floor in range(0, N_FLOORS)],
                                'buttons_down': [0 for floor in range(0, N_FLOORS)],
                                'slave_id': 0,
                                'last_floor': 0,
                                'next_floor': 0,
                                'direction': 0}

        self.__master_message = {'orders_up': [0 for floor in range(0, N_FLOORS)],
                                 'orders_down': [0 for floor in range(0, N_FLOORS)],
                                 'master_id': 0}

        self.__thread_buffering_master = Thread(target=self.__buffering_master_messages_thread, args=(),
                                                name="__buffering_master_messages_thread")
        self.__thread_buffering_slave = Thread(target=self.__buffering_slave_messages_thread, args=(),
                                               name="__buffering_slave_messages_thread")
        self.__thread_master_alive = Thread(target=self.__master_alive_thread, args=(), name="__master_alive_thread")

        self.__downtime_no_active_master = time.time() + 2

    def no_active_master(self):
        if self.__master_alive_thread_started is not True:
            self.__start(self.__thread_master_alive)

        with self.__no_active_master_key:
            return self.__no_active_master

    def connected_to_network(self):
        with self.__is_connected_to_network_key:
            return self.__is_connected_to_network

    def send_to_master(self, buttons_up, buttons_down, slave_id, last_floor, next_floor, direction):
        floor_up = str()
        floor_down = str()

        for floor in buttons_up:
            floor_up += str(floor)

        for floor in buttons_down:
            floor_down += str(floor)

        message = "%s%s%i%i%i%i" % (floor_up, floor_down, slave_id, last_floor, next_floor, direction)

        self.__send(message, SLAVE_TO_MASTER_PORT)

    def send_to_slave(self, orders_up, orders_down, master_id):
        message = str()

        master_id = str(master_id)

        for order in orders_up:
            message += str(order)

        for order in orders_down:
            message += str(order)

        message += master_id

        self.__send(message, MASTER_TO_SLAVE_PORT)

    def receive_from_master(self):
        message = self.__read_message(MASTER_TO_SLAVE_PORT)

        if message is not None:

            for floor in range(0, N_FLOORS):
                self.__master_message['orders_up'][floor] = int(message[floor])

            for floor in range(0, N_FLOORS):
                self.__master_message['orders_down'][floor] = int(message[4 + floor])

            self.__master_message['master_id'] = int(message[8])

            return self.__master_message

    def receive_from_slave(self):
        message = self.__read_message(SLAVE_TO_MASTER_PORT)

        if message is not None:

            for floor in range(0, N_FLOORS):
                self.__slave_message['buttons_up'][floor] = int(message[floor])
                self.__slave_message['buttons_down'][floor] = int(message[4 + floor])

            self.__slave_message['slave_id'] = int(message[8])
            self.__slave_message['last_floor'] = int(message[9])
            self.__slave_message['next_floor'] = int(message[10])
            self.__slave_message['direction'] = int(message[11])

            return self.__slave_message

    def __send(self, data, port):
        try:
            send = ('<broadcast>', port)
            udp = socket(AF_INET, SOCK_DGRAM)
            udp.setsockopt(SOL_SOCKET, SO_BROADCAST, 1)
            message = '<%s;%s>' % (str(len(data)), data)
            udp.sendto(message, send)
            udp.close()
            with self.__is_connected_to_network_key:
                self.__is_connected_to_network = True

        except IOError as error:
            print "MessageHandler.__send: Failed. Network down?"
            print error
            print "Sleeping 1 sec.."

            with self.__is_connected_to_network_key:
                self.__is_connected_to_network = False
            time.sleep(1)

    def __read_message(self, port):
        ###### START THREADS IF NOT ALREADY RUNNING ######
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

    def __start(self, thread):
        try:
            thread.daemon = True
            thread.start()

        except StandardError as error:
            print "MessageHandler.__start(): Thread: %s operation failed" % thread.name
            print error
            interrupt_main()

    def __buffering_master_messages_thread(self):
        try:
            self.__master_thread_started = True

            try:
                port = ('', SLAVE_TO_MASTER_PORT)
                udp = socket(AF_INET, SOCK_DGRAM)
                udp.bind(port)
                udp.setsockopt(SOL_SOCKET, SO_BROADCAST, 1)

            except IOError as error:
                print "MessageHandler.__buffering_master_messages_thread: Failed setting up udp sockets"
                print error
                interrupt_main()

            while True:
                try:
                    data, address = udp.recvfrom(1024)

                except IOError as error:
                    print "MessageHandler.__buffering_master_messages_thread: udp.recvfrom(1024) failed!"
                    print error
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
            print "MessageHandler.__buffering_master_messages"
            print error
            interrupt_main()

    def __buffering_slave_messages_thread(self):
        try:
            self.__slave_thread_started = True

            try:
                port = ('', MASTER_TO_SLAVE_PORT)
                udp = socket(AF_INET, SOCK_DGRAM)
                udp.bind(port)
                udp.setsockopt(SOL_SOCKET, SO_BROADCAST, 1)

            except IOError as error:
                print "MessageHandler.__buffering_slave_messages_thread: Failed setting up udp sockets"
                print error
                interrupt_main()

            # downtime_no_active_master = time.time() + 2 ################################ glemt når alive_thread ble laget?

            while True:
                try:
                    data, address = udp.recvfrom(1024)

                except IOError as error:
                    print "MessageHandler.__buffering_slave_messages_thread: udp.recvfrom(1024) failed!"
                    print error
                    print "Sleeping 1 sec.."
                    time.sleep(1)

                message = self.__errorcheck(data)

                if message is not None:
                    self.__downtime_no_active_master = time.time() + 2
                    with self.__no_active_master_key:
                        self.__no_active_master = False

                    with self.__receive_buffer_slave_key:
                        if message in self.__receive_buffer_slave:
                            pass
                        else:
                            self.__receive_buffer_slave.append(message)

        except StandardError as error:
            print "MessageHandler.__buffering_slave_messages"
            print error
            interrupt_main()

    def __master_alive_thread(self):
        try:
            __master_alive_thread_watchdog = watchdogs.ThreadWatchdog(1,"watchdog event: MessageHandler.__master_alive_thread")
            __master_alive_thread_watchdog.start_watchdog()

            self.__master_alive_thread_started = True

            while True:
                time.sleep(TICK * 100)
                __master_alive_thread_watchdog.pet_watchdog()

                if self.__downtime_no_active_master < time.time():
                    with self.__no_active_master_key:
                        self.__no_active_master = True

        except StandardError as error:
            print "MessageHandler.__master_alive"
            print error
            interrupt_main()

    def __errorcheck(self, data):
        ###### CHECKS THAT THE MESSAGE IS FOR THIS SYSTEM # WITHOUT OBVIOUS ERRORS ######
        if data[0] == '<' and data[len(data) - 1] == '>':
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
                for n in range(separator_pos, len(data) - 1):
                    message += data[n]
                return message
            else:
                return None
        else:
            return None
