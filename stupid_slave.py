from slave_driver import SlaveDriver
from message_handler import MessageHandler
from constants import SLAVE_TO_MASTER_PORT, MASTER_TO_SLAVE_PORT, MY_ID, N_FLOORS
import time



def main():

	#instantiating classes
	message_handler = MessageHandler(MY_ID)
	slave_driver = SlaveDriver()
	#slave_handler = SlaveHandler()

	#acknowledge = 4
	#run_floor = 0
	#run_button = 0
	#old_f = None
	#old_but = None
	is_master = False
	floor_up = [0]*4
	floor_down = [0]*4
	master_id = 10
	changing_master = True
	last_master_id = 0
	while True:

		#if slave_handler.check_slave_alive() == MY_ID:
		#	active_slave = True
		
		position = slave_driver.read_position()

		master_message = message_handler.receive_from_master()

		(floor,button) = slave_driver.pop_floor_panel_queue()

		if floor is not None:
			if button == 0:
				floor_up[floor] = 1
			elif button == 1: 
				floor_down[floor] = 1 	
			

		for i in range (0,4):
			if (master_message['master_floor_up'][i] != 0):
				floor_up[i] = 0

			if (master_message['master_floor_down'][i] != 0):
				floor_down[i] = 0
		
		#time.sleep(0.3)

		message_handler.send_to_master(floor_up,floor_down,MY_ID,position[0],position[1],position[2],master_message['queue_id'])
		
		print "floor_up: " +  str(floor_up)
		print "floor_down: " + str(floor_down)


		'''
		(run_floor,run_button) = message_handler.get_my_master_order()
		
		print run_floor
		print run_button

		if run_floor is not None:
			slave_driver.queue_elevator_run(run_floor,run_button)
		'''

		master_queue = master_message['master_floor_up'][:] + master_message['master_floor_down'][:]

		print "master_queue: " + str(master_queue) 
		
		#if master_id == MY_ID:
		#	is_master = True

		master_id = master_message['master_id']

		if last_master_id !=  master_id: 
			changing_master = True
		
		if changing_master:	
			
			my_master_queue = slave_driver.read_saved_master_queue()
			print "CHANGING MASTER STATE = TRUE -> my_master_queue: " + str(my_master_queue)
			message_handler.send_to_master(my_master_queue[0:4],my_master_queue[4:8],MY_ID,position[0],position[1],position[2],master_message['queue_id'])
			orders_ok = True
			for floor in range(0,N_FLOORS):
				if ((my_master_queue[floor] > 0) and (master_message['master_floor_up'][floor] == 0)) and ((my_master_queue[floor+4] > 0) and (master_message['master_floor_down'][floor] == 0)):
					orders_ok = False 
			if orders_ok: 
				is_master = False 
				changing_master = False

		if not changing_master:
			slave_driver.master_queue_elevator_run(master_queue)

		#print ['floor_up:'] + master_message['master_floor_up'] + ['floor_down:'] + master_message['master_floor_down'] 
		#print master_message['queue_id']
				
		time.sleep(0.1)

		last_master_id = master_id

if __name__ == "__main__":
    main()