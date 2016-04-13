from slave_driver import SlaveDriver
from message_handler import MessageHandler
from ported_driver.constants import N_FLOORS
from config_parameters import MY_ID, TICK, N_ELEVATORS
import time

def main():
	try:
		message_handler = MessageHandler()
		slave_driver = SlaveDriver()

		orders_ok = True

		while True:
			time.sleep(TICK*N_ELEVATORS)

			position = slave_driver.read_position()
			master_message = message_handler.receive_from_master()

			if message_handler.no_active_master():
				slave_driver.set_offline_mode(True)
			else:
				slave_driver.set_offline_mode(False)	
			
			if master_message is not None:	
				if slave_driver.changing_master(master_message['master_id'],orders_ok):	
					print "CHANGING MASTER"
					(unfinished_orders_up,unfinished_orders_down) = slave_driver.unfinished_orders()
					
					message_handler.send_to_master(unfinished_orders_up,unfinished_orders_down,MY_ID,position[0],position[1],position[2])
					orders_ok = True
					
					for floor in range(0,N_FLOORS):
						if ( (unfinished_orders_up[floor] > 0) and (master_message['orders_up'][floor] == 0) ) or ( (unfinished_orders_down[floor] > 0) and (master_message['orders_down'][floor] == 0) ):
							orders_ok = False 

				else:
					slave_driver.master_order_run_elevator(master_message['orders_up'][:],master_message['orders_down'][:])	

					(floor_up,floor_down) = slave_driver.get_floor_panel()

					move_timeout = slave_driver.read_move_timeout()
			
					if (move_timeout == False):
						message_handler.send_to_master(floor_up,floor_down,MY_ID,position[0],position[1],position[2])
		
	###### ALL THREADS MAY INTERRUPT MAIN USING A KEYBOARD INTERRUPT EXCEPTION ######
	except KeyboardInterrupt:
		pass

	except StandardError as error:
		print error
	finally:
		print "Exiting slave.py..."

if __name__ == "__main__":
    main()