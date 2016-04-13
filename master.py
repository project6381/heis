from master_handler import MasterHandler
from message_handler import MessageHandler
from ported_driver.constants import N_FLOORS
from config_parameters import N_ELEVATORS, MY_ID, TICK
import time

def main():
	try:
		message_handler = MessageHandler()
		master_handler = MasterHandler()

		startup = True
		startup_time = time.time() + 1
		
		print "Beginning master startup sequence..."

		while startup:
			time.sleep(TICK*100)

			###### SEND EMPTY MESSAGE WITH UNUSED ID TO PUT SLAVES IN 'CHANGING MASTER' STATE ######
			message_handler.send_to_slave([0 for floor in range(0,N_FLOORS)],[0 for floor in range(0,N_FLOORS)],N_ELEVATORS+1)
			
			###### READ MESSAGES TO REDUCE AMOUNT OF OLD MESSAGES IN RECEIVE BUFFER ######
			message_handler.receive_from_slave()
			
			if startup_time < time.time():
				startup = False

			if not message_handler.connected_to_network():
				raise KeyboardInterrupt
		
		print "Startup sequence finished!"

		while True:
			time.sleep(TICK)

			if not message_handler.connected_to_network():
				raise KeyboardInterrupt

			master_handler.i_am_alive()

			slave_message = message_handler.receive_from_slave()

			if slave_message is not None:
				master_handler.process_slave_event(slave_message)		

			if master_handler.active_master() == MY_ID:

				(assigned_orders_up,assigned_orders_down) = master_handler.current_assigned_orders()

				message_handler.send_to_slave(assigned_orders_up,assigned_orders_down,MY_ID)

	###### ALL THREADS MAY INTERRUPT MAIN USING A KEYBOARD INTERRUPT EXCEPTION ######							
	except KeyboardInterrupt:
		pass 

	except StandardError as error:
		print error
	finally:
		print "Exiting master.py..."
				
if __name__ == "__main__":
    main()