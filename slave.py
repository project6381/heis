import time

from slave_driver import SlaveDriver
from message_handler import MessageHandler
from ported_driver.constants import N_FLOORS
from config_parameters import MY_ID, TICK, N_ELEVATORS


def main():
	try:
		message_handler = MessageHandler()
		slave_driver = SlaveDriver()

		console_message = "Undefined console_message"
		last_console_message = "Undefined console_message"

		while True:
			time.sleep(TICK*N_ELEVATORS)

			position = slave_driver.read_position()
			master_message = message_handler.receive_from_master()

			if message_handler.no_active_master():
				slave_driver.set_offline_mode(True)
				console_message = "Slave (ID: " + str(MY_ID) + "): offline mode active!"
			else:
				slave_driver.set_offline_mode(False)
				console_message = "Slave (ID: " + str(MY_ID) + "): offline mode inactive..."	
			
			if master_message is not None:	
				if slave_driver.changing_master(master_message):	
					
					###### SENDS UNFINISHED ORDERS AS BUTTON PRESSES ######
					(unfinished_orders_up,unfinished_orders_down) = slave_driver.unfinished_orders()
					message_handler.send_to_master(unfinished_orders_up,unfinished_orders_down,MY_ID,position[0],position[1],position[2])			 

				else:
					slave_driver.update_master_orders(master_message['orders_up'][:],master_message['orders_down'][:])	

					(buttons_up,buttons_down) = slave_driver.external_buttons_pressed()
			
					if not slave_driver.move_timeout():
						message_handler.send_to_master(buttons_up,buttons_down,MY_ID,position[0],position[1],position[2])
						print "ERROR! Elevator not moving?"

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