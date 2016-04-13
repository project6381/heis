import thread
from threading import Timer


class ThreadWatchdog(object):
    def __init__(self, time, exit_message):
        self._time = time
        self._exit_message = exit_message
        return

    def start_watchdog(self):
        self._timer = Timer(self._time, self.__watchdog_event)
        self._timer.daemon = True
        self._timer.start()
        return

    def pet_watchdog(self):
        self.stop_watchdog()
        self.start_watchdog()
        return

    def __watchdog_event(self):
        print self._exit_message
        self.stop_watchdog()
        thread.interrupt_main()
        return

    def stop_watchdog(self):
        self._timer.cancel()
