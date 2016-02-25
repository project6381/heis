import ElevInterface
import PanelInterface
import constants

elevator = ElevInterface.ElevInterface()
panel = PanelInterface.PanelInterface()

def go_to_floor(floor):
	
	
	elevator.set_motor_direction(constants.DIRN_UP)


	while True:
		currentFloor = elevator.get_floor_sensor_signal()

		if currentFloor >= 0:
			if currentFloor == floor:
				elevator.set_motor_direction(constants.DIRN_STOP)
				print 'you reached your destination'
				panel.set_door_open_lamp(1)
				return 0
			elif currentFloor < floor:
				panel.set_door_open_lamp(0)
				elevator.set_motor_direction(constants.DIRN_UP)
				print 'goin up to %i, last floor is %i' % (floor, currentFloor) 
			elif currentFloor > floor:
				panel.set_door_open_lamp(0)
				elevator.set_motor_direction(constants.DIRN_DOWN)
				print 'goin down to %i, last floor is %i' % (floor, currentFloor)

		if panel.get_stop_signal() == 1:
			elevator.set_motor_direction(constants.DIRN_STOP)
			return 0	
		

