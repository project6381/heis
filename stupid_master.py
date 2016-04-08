from master_handler import MasterHandler
from message_handler import MessageHandler
from constants import SLAVE_TO_MASTER_PORT, MASTER_TO_SLAVE_PORT, DIRN_DOWN, DIRN_UP, DIRN_STOP, N_ELEVATORS, MY_ID
import time
from collections import Counter


def main():
	SLAVE_TIMEOUT = 2
	SLAVE_MESSAGE_TIMEOUT = 1
	#instantiating classes
	message_handler = MessageHandler()
	master_handler = MasterHandler()
	active_master = False

	while True:
	
		master_handler.update_master_alive(MY_ID)

		if master_handler.check_master_alive() == MY_ID:
			active_master = True
		else:
			slave_message = message_handler.receive_from_slave()

			if slave_message is not None:
				master_handler.update_elevator_online(slave_message['slave_id'])	
			#	master_handler.__elevator_online[slave_message['slave_id']-1] = 1
			#	master_handler.__downtime_elevator_online[slave_message['slave_id']-1] = time.time() + SLAVE_TIMEOUT

			

		print "I am NOT master, my id is: " + str(MY_ID)
		#print elevator_online
		time.sleep(0.02)

		while active_master:

			#print "I AM master, my id is: " + str(my_id)
			
			master_handler.update_master_alive(MY_ID)
			slave_message = message_handler.receive_from_slave()			
			if slave_message is not None:
			
				
				master_handler.clear_completed_orders(slave_message['direction'], slave_message['last_floor'], slave_message['next_floor'])

				master_handler.update_elevator_position(slave_message['slave_id'],slave_message['last_floor'],slave_message['next_floor'],slave_message['direction'])
				
				master_handler.add_new_orders(slave_message['slave_floor_up'],slave_message['slave_floor_down'])
								
				master_handler.update_sync_state(slave_message['orders_id'],slave_message['slave_id'])
				


			(elevator_orders, orders_id) = master_handler.fetch_for_faen()
			
			

			message_handler.send_to_slave(elevator_orders,MY_ID,orders_id)
			


			if master_handler.check_master_alive() != MY_ID:
				active_master = False

			time.sleep(0.02)





if __name__ == "__main__":
    main()