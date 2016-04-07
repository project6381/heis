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
	orders_id = 1

	button_orders = [0]*8
	last_button_orders = [0]*8
	elevator_positions = [0,0,1]*N_ELEVATORS
	elevator_orders = [0]*8
	last_elevator_orders = [0]*8
	elevator_online = [0]*N_ELEVATORS
	elevators_received_current_queue_id = [0]*N_ELEVATORS
	active_slaves = 0
	arrived = 0
	last_direction = 0
	active_master = False
	downtime_elevator_online = [time.time() + 3]*N_ELEVATORS
	downtime_queue_id = time.time() + 3
	timeout_active_slaves = 0

	while True:
	
		master_handler.update_master_alive(MY_ID)


		if master_handler.check_master_alive() == MY_ID:
			active_master = True




		print "I am NOT master, my id is: " + str(MY_ID)

		time.sleep(0.02)

		while active_master:

			#print "I AM master, my id is: " + str(my_id)
			
			master_handler.update_master_alive(MY_ID)
			slave_message = message_handler.receive_from_slave()
			if slave_message is not None:
			
				last_direction = slave_message['direction']

				if slave_message['last_floor'] == slave_message['next_floor']:
					arrived = slave_message['last_floor']	
					if (last_direction == DIRN_UP) or (last_direction == DIRN_STOP):
						button_orders[arrived] = 0
					if (last_direction == DIRN_DOWN) or (last_direction == DIRN_STOP):
						button_orders[arrived+4] = 0
				
				slave_id = slave_message['slave_id']
				#print str(slave_id) + '  slave id' 

				elevator_positions[slave_id-1] = [slave_message['last_floor'],slave_message['next_floor'],slave_message['direction']] 
				
				''' Check for new orders '''
				for i in range(0,4):
					if slave_message['slave_floor_up'][i] == 1: 
						button_orders[i] = 1

				for i in range(0,4):
					if (slave_message['slave_floor_down'][i] == 1): 
						button_orders[i+4] = 1			



				#print str(button_orders) + ' button_orders'
				#button_orders = slave_message['slave_floor_up'] + slave_message['slave_floor_down']				

				if orders_id == slave_message['orders_id']:
					elevators_received_current_queue_id[slave_id-1] = 1

				active_slaves = elevator_online.count(1)

				
				if (button_orders != last_button_orders) and (active_slaves == elevators_received_current_queue_id.count(1) or timeout_active_slaves == 1): # and (0 not in elevators_queue_id):
					print '1111111111111111111111111111111111'
					orders_id += 1
					if orders_id > 9999: 
						orders_id = 1
					last_button_orders = button_orders[:]
					print 'hei'
					downtime_queue_id = time.time() + SLAVE_MESSAGE_TIMEOUT
					timeout_active_slaves = 0

				downtime_elevator_online[slave_id-1] = time.time() + SLAVE_TIMEOUT
				elevator_online[slave_id-1] = 1
								
				elevator_orders = master_handler.order_elevator(last_button_orders, elevator_positions, elevator_online)
				print elevator_online
				print button_orders
			
			message_handler.send_to_slave(elevator_orders,MY_ID,orders_id)
			
			for i in range(0,N_ELEVATORS):
				if downtime_elevator_online[i] < time.time():
					elevator_online[i] = 0

			if downtime_queue_id < time.time():
				for i in range(0,N_ELEVATORS):
					timeout_active_slaves = 1


			time.sleep(0.02)





if __name__ == "__main__":
    main()