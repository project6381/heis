from time import sleep
from threading import Timer
import thread
import signal

#Kilde for klasse WatchdogTimer: https://dzone.com/articles/simple-python-watchdog-timer
class WatchdogTimer(Exception):

    def __init__(self, time):
        self.time = time

    def __enter__(self):
        signal.signal(signal.SIGALRM, self.handler)
        signal.alarm(self.time)
 
    def __exit__(self, type, value, traceback):
        signal.alarm(0)
    
    def handler(self, signum, frame):
        raise self
 
    def __str__(self):
        return "WatchdogTimer: The code you executed took more than %ds to complete" % self.time

# Kilde for klassen ThreadWatchdog: http://liveincode.blogspot.com/2012/11/watchdog-timer-in-python.html
class ThreadWatchdog(object):
    
    def __init__(self, time, exit_message):
        ''' Class constructor. The "time" argument has the units of seconds. '''
        self._time = time
        self._exit_message = exit_message
        return
        
    def StartWatchdog(self):
        ''' Starts the watchdog timer. '''
        self._timer = Timer(self._time, self._WatchdogEvent)
        self._timer.daemon = True
        self._timer.start()
        return
        
    def PetWatchdog(self):
        ''' Reset watchdog timer. '''
        self.StopWatchdog()
        self.StartWatchdog()
        return
        
    def _WatchdogEvent(self):
        '''
        This internal method gets called when the timer triggers. A keyboard 
        interrupt is generated on the main thread. The watchdog timer is stopped 
        when a previous event is tripped.
        '''
        print self._exit_message
        self.StopWatchdog()
        thread.interrupt_main()
        return

    def StopWatchdog(self):
        ''' Stops the watchdog timer. '''
        self._timer.cancel()