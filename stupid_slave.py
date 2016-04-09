from slave_driver import SlaveDriver
from message_handler import MessageHandler
from constants import SLAVE_TO_MASTER_PORT, MASTER_TO_SLAVE_PORT, MY_ID, N_FLOORS
import time
import sys
import subprocess


def main():

	#instantiating classes
	message_handler = MessageHandler()
	slave_driver = SlaveDriver()
	orders_id = 0

	while True:
		#try:

			position = slave_driver.read_position()

			master_message = message_handler.receive_from_master()
			
			if master_message is not None:	

				slave_driver.clear_floor_panel(master_message['orders_up'][:],master_message['orders_down'][:])
						
				orders_id = master_message['orders_id']
				
				if slave_driver.changing_master(master_message['master_id']):	
					
					my_master_queue = slave_driver.read_saved_master_queue()
					print "CHANGING MASTER STATE = TRUE -> my_master_queue: " + str(my_master_queue)
					for i in range(0,8):
						if my_master_queue[i] > 0:
							my_master_queue[i]=1
					message_handler.send_to_master(my_master_queue[0:4],my_master_queue[4:8],MY_ID,position[0],position[1],position[2],master_message['orders_id'])
					orders_ok = True
					
					for order in range(0,N_FLOORS):
						if ( (my_master_queue[order] > 0) and (master_message['orders_up'][order] == 0) ) and ( (my_master_queue[4+order] > 0) and (master_message['orders_down'][order]) ):
							orders_ok = False 
					if orders_ok: 
						#is_master = False 
						changing_master = False

				else:
					#print master_message['orders_up'][:] + master_message['orders_down'][:]

					slave_driver.master_queue_elevator_run(master_message['orders_up'][:] + master_message['orders_down'][:])	

			(floor_up,floor_down) = slave_driver.get_floor_panel()

			#print floor_up + floor_down + ['pikk']

			message_handler.send_to_master(floor_up,floor_down,MY_ID,position[0],position[1],position[2],orders_id)
			time.sleep(0.1)

		#except KeyboardInterrupt:
		#	pass
		#except StandardError as error:
		#	print error
		#finally:
		#	print "exiting main"

if __name__ == "__main__":
    main()