from master_handler import MasterHandler
from message_handler import MessageHandler
from ported_driver.constants import N_FLOORS
from config_parameters import N_ELEVATORS, MY_ID, TICK
import time

def main():
	try:
		message_handler = MessageHandler()
		master_handler = MasterHandler()
		
		active_master = False
		startup = True
		startup_time = time.time() + 1
		
		print "Beginning master startup sequence..."

		while startup:
			time.sleep(TICK*100)

			###### EMPTY MASTER MESSAGE WITH UNUSED ID # TO PUT SLAVES IN 'CHANGING MASTER' STATE ######
			message_handler.send_to_slave([0 for floor in range(0,N_FLOORS)],[0 for floor in range(0,N_FLOORS)],N_ELEVATORS+1)
			
			###### READ MESSAGES TO REDUCE AMOUNT OF OLD MESSAGES IN BUFFER ######
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

			if master_handler.active_master() == MY_ID:
				active_master = True
			else:
				active_master = False

			slave_message = message_handler.receive_from_slave()

			if slave_message is not None:
				master_handler.update_slave_online(slave_message['slave_id'])			

			if active_master:

				if slave_message is not None:
								
					master_handler.process_slave_event(slave_message)
				
				(orders_up,orders_down) = master_handler.current_orders()

				message_handler.send_to_slave(orders_up,orders_down,MY_ID)
				
					
		
	except KeyboardInterrupt:
		pass
	except StandardError as error:
		print error
	finally:
		print "Exiting master.py.."
				

if __name__ == "__main__":
    main()