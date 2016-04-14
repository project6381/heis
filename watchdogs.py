import thread

from threading import Timer


class ThreadWatchdog(object):
    def __init__(self, time, exit_message):
        self.__time = time
        self.__exit_message = exit_message
        
    def start_watchdog(self):
        self.__timer = Timer(self.__time, self.__watchdog_event)
        self.__timer.daemon = True
        self.__timer.start()
        
    def pet_watchdog(self):
        self.stop_watchdog()
        self.start_watchdog()

    def stop_watchdog(self):
        self.__timer.cancel()

    def __watchdog_event(self):
        print self.__exit_message
        self.stop_watchdog()
        thread.interrupt_main()