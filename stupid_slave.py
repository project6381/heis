from slave_driver import SlaveDriver
from message_handler import MessageHandler
from constants import SLAVE_TO_MASTER_PORT, MASTER_TO_SLAVE_PORT, MY_ID, N_FLOORS
import time



def main():

	#instantiating classes
	message_handler = MessageHandler()
	slave_driver = SlaveDriver()
	is_master = False
	floor_up = [0]*4
	floor_down = [0]*4
	changing_master = False
	last_master_id = 0
	queue_id = 0

	while True:

		#if slave_handler.check_slave_alive() == MY_ID:
		#	active_slave = True
		

		position = slave_driver.read_position()

		(floor,button) = slave_driver.pop_floor_panel_queue()
		if floor is not None:
			if button == 0:
				floor_up[floor] = 1
			elif button == 1: 
				floor_down[floor] = 1 	


		master_message = message_handler.receive_from_master()
		if master_message is not None:	

			for i in range (0,4):
				if (master_message['master_floor_up'][i] != 0):
					floor_up[i] = 0

				if (master_message['master_floor_down'][i] != 0):
					floor_down[i] = 0
			

					
			queue_id = master_message['queue_id']
			master_queue = master_message['master_floor_up'][:] + master_message['master_floor_down'][:]

			#if master_message['master_id'] == MY_ID:
			#	is_master = True

			#if last_master_id !=  master_message['master_id']: 
			#	changing_master = True
			
			if changing_master:	
				
				my_master_queue = slave_driver.read_saved_master_queue()
				print "CHANGING MASTER STATE = TRUE -> my_master_queue: " + str(my_master_queue)
				for i in range(0,8):
					if my_master_queue[i] > 0:
						my_master_queue[i]=1
				message_handler.send_to_master(my_master_queue[0:4],my_master_queue[4:8],MY_ID,position[0],position[1],position[2],master_message['queue_id'])
				orders_ok = True
				for floor in range(0,N_FLOORS):
					if ((my_master_queue[floor] > 0) and (master_message['master_floor_up'][floor] == 0)) and ((my_master_queue[floor+4] > 0) and (master_message['master_floor_down'][floor] == 0)):
						orders_ok = False 
				if orders_ok: 
					is_master = False 
					changing_master = False

			else:
				print master_queue
				slave_driver.master_queue_elevator_run(master_queue)

			#print ['floor_up:'] + master_message['master_floor_up'] + ['floor_down:'] + master_message['master_floor_down'] 
			#print master_message['queue_id']

			last_master_id = master_message['master_id']

		message_handler.send_to_master(floor_up,floor_down,MY_ID,position[0],position[1],position[2],queue_id)
		time.sleep(0.1)
if __name__ == "__main__":
    main()