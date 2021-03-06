from master_handler import MasterHandler
from message_handler import MessageHandler
from ported_driver.constants import DIRN_DOWN, DIRN_UP, DIRN_STOP
from config_parameters import SLAVE_TO_MASTER_PORT, MASTER_TO_SLAVE_PORT, N_ELEVATORS, MY_ID, TICK
import time
from collections import Counter
import sys
import subprocess

def main():
	SLAVE_TIMEOUT = 2
	SLAVE_MESSAGE_TIMEOUT = 1
	#instantiating classes
	message_handler = MessageHandler()
	master_handler = MasterHandler()
	active_master = False

	while True:
		#try:
			time.sleep(TICK)

			master_handler.update_master_alive(MY_ID)

			if master_handler.check_master_alive() == MY_ID:
				active_master = True
			else:
				slave_message = message_handler.receive_from_slave()

				if slave_message is not None:
					master_handler.update_elevator_online(slave_message['slave_id'])			

			print "I am NOT master, my id is: " + str(MY_ID)

			#print elevator_online
			
			while active_master:
				time.sleep(TICK)
				#print "I AM master, my id is: " + str(my_id)

				
				master_handler.update_master_alive(MY_ID)
				slave_message = message_handler.receive_from_slave()			
				if slave_message is not None:
				
					
					master_handler.clear_completed_orders(slave_message['direction'], slave_message['last_floor'], slave_message['next_floor'])

					master_handler.update_elevator_position(slave_message['slave_id'],slave_message['last_floor'],slave_message['next_floor'],slave_message['direction'])
					
					master_handler.add_new_orders(slave_message['slave_floor_up'],slave_message['slave_floor_down'])
									
					master_handler.update_sync_state(slave_message['orders_id'],slave_message['slave_id'])
					

				(orders_up,orders_down,orders_id) = master_handler.get_orders()			

				message_handler.send_to_slave(orders_up,orders_down,MY_ID,orders_id)
				
				if master_handler.check_master_alive() != MY_ID:
					active_master = False


		
		#except KeyboardInterrupt:
		#	pass
		#except StandardError as error:
		#	print error
		#finally:
		#	print "exiting main"
				

if __name__ == "__main__":
    main()