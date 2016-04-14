import time

import watchdogs

from slave_handler import SlaveHandler
from message_handler import MessageHandler
from ported_driver.constants import N_FLOORS
from config_parameters import MY_ID, TICK, N_ELEVATORS


def main():
	try:
		main_watchdog = watchdogs.ThreadWatchdog(3,"watchdog event: main_watchdog")
		main_watchdog.start_watchdog()

		message_handler = MessageHandler()
		slave_handler = SlaveHandler()

		console_message = "Undefined console_message"
		last_console_message = "Undefined console_message"

		while True:
			time.sleep(TICK*N_ELEVATORS)
			main_watchdog.pet_watchdog()

			position = slave_handler.read_position()
			master_message = message_handler.receive_from_master()

			if message_handler.no_active_master():
				slave_handler.set_offline_mode(True)
				console_message = "Slave (ID: " + str(MY_ID) + "): offline mode active!"
			else:
				slave_handler.set_offline_mode(False)
				console_message = "Slave (ID: " + str(MY_ID) + "): offline mode inactive..."	
			
			if master_message is not None:	
				if slave_handler.changing_master(master_message):	
					
					###### SENDS UNFINISHED ORDERS AS BUTTON PRESSES ######
					(unfinished_orders_up,unfinished_orders_down) = slave_handler.unfinished_orders()
					message_handler.send_to_master(unfinished_orders_up,unfinished_orders_down,MY_ID,position[0],position[1],position[2])			 

				else:
					slave_handler.update_master_orders(master_message['orders_up'][:],master_message['orders_down'][:])	

					(buttons_up,buttons_down) = slave_handler.external_buttons_pressed()
			
					if slave_handler.movement_timeout():
						print "ERROR! Elevator not moving?"
					else:
						message_handler.send_to_master(buttons_up,buttons_down,MY_ID,position[0],position[1],position[2])						

			if console_message != last_console_message:
				print console_message
				last_console_message = console_message

	###### ALL THREADS MAY INTERRUPT MAIN USING A KEYBOARD INTERRUPT EXCEPTION ######
	except KeyboardInterrupt:
		pass
	
	except StandardError as error:
		print error
	finally:
		print "Exiting slave.py..."

if __name__ == "__main__":
    main()