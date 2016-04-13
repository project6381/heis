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
				slave_message = message_handler.receive_from_slave()

				if slave_message is not None:
					master_handler.update_slave_online(slave_message['slave_id'])			

			while active_master:
				time.sleep(TICK)

				if not message_handler.connected_to_network():
					raise KeyboardInterrupt
				
				master_handler.i_am_alive()

				slave_message = message_handler.receive_from_slave()

				if slave_message is not None:
								
					master_handler.clear_completed_orders(	slave_message['direction'],
															slave_message['last_floor'],
															slave_message['next_floor'])

					master_handler.update_elevator_position(slave_message['slave_id'],slave_message['last_floor'],slave_message['next_floor'],slave_message['direction'])
					
					master_handler.add_new_orders(slave_message['slave_floor_up'],slave_message['slave_floor_down'])
									
					master_handler.update_slave_online(slave_message['slave_id'])
				
				(orders_up,orders_down) = master_handler.assign_orders()

				message_handler.send_to_slave(orders_up,orders_down,MY_ID)
				
				if master_handler.active_master() != MY_ID:
					active_master = False
		
	except KeyboardInterrupt:
		pass
	except StandardError as error:
		print error
	finally:
		print "Exiting master.py.."
				

if __name__ == "__main__":
    main()