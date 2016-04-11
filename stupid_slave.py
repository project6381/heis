from slave_driver import SlaveDriver
from message_handler import MessageHandler
from ported_driver.constants import N_FLOORS
from config_parameters import SLAVE_TO_MASTER_PORT, MASTER_TO_SLAVE_PORT, MY_ID
import time
import sys
import subprocess


def main():

	time.sleep(4)

	#instantiating classes
	message_handler = MessageHandler()
	slave_driver = SlaveDriver()
	orders_id = 0
	downtime_send = time.time()
	orders_ok = True


	while True:
		#try:

			position = slave_driver.read_position()
			master_message = message_handler.receive_from_master()
			
			if master_message is not None:	

				#slave_driver.clear_floor_panel(master_message['orders_up'][:],master_message['orders_down'][:])
						
				orders_id = master_message['orders_id']
				print str(orders_ok) + '    '+ str(master_message['master_id'])
				if slave_driver.changing_master(master_message['master_id'],orders_ok):	
					
					(my_master_orders_up,my_master_orders_down) = slave_driver.read_saved_master_queue()
					print "CHANGING MASTER STATE = TRUE -> my_master_queue: " + str(my_master_orders_up) + str(my_master_orders_down) + " master_message" + str(master_message['orders_up']) + str(master_message['orders_down'])
					for floor in range(0,N_FLOORS):
						if my_master_orders_up[floor] > 0:
							my_master_orders_up[floor]=1
						if my_master_orders_down[floor] > 0:
							my_master_orders_down[floor]=1
					message_handler.send_to_master(my_master_orders_up,my_master_orders_down,MY_ID,position[0],position[1],position[2],master_message['orders_id'])
					orders_ok = True
					
					for floor in range(0,N_FLOORS):
						if ( (my_master_orders_up[floor] > 0) and (master_message['orders_up'][floor] == 0) ) or ( (my_master_orders_down[floor] > 0) and (master_message['orders_down'][floor] == 0) ):
							orders_ok = False 

				else:
					slave_driver.master_order_run_elevator(master_message['orders_up'][:],master_message['orders_down'][:])	

					(floor_up,floor_down) = slave_driver.get_floor_panel()
			
					if downtime_send < time.time():
						message_handler.send_to_master(floor_up,floor_down,MY_ID,position[0],position[1],position[2],orders_id)
						downtime_send = time.time() + 0.1


			time.sleep(0.0123)

		#except KeyboardInterrupt:
		#	pass
		#except StandardError as error:
		#	print error
		#finally:
		#	print "exiting main"

if __name__ == "__main__":
    main()