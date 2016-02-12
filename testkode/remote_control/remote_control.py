import ElevInterface as elev
import PanelInterface as pan
import constants as const
import broadcast

def get_order():
	floor = int(broadcast.recieve())
	print floor
	return floor

def go_to_floor(floor):
	elevInt = elev.ElevInterface()
	panelInt = pan.PanelInterface()

	elevInt.set_motor_direction(const.DIRN_UP)
	
	while True:
		currFloor = elevInt.get_floor_sensor_signal()
		if currFloor >= 0:
			if currFloor == floor:
				elevInt.set_motor_direction(const.DIRN_STOP)
				print 'same floor nigga'
				return 0
			elif currFloor < floor:
				elevInt.set_motor_direction(const.DIRN_UP)
				print 'goin up to %i, with current floor %i' % (floor, currFloor) 
			elif currFloor > floor:
				elevInt.set_motor_direction(const.DIRN_DOWN)
				print 'goin down to %i, with current floor %i' % (floor, currFloor)
		if panelInt.get_stop_signal() == 1:
			elevInt.set_motor_direction(const.DIRN_STOP)
			return 0

if __name__ == "__main__":
	
	go_to_floor(1)
	
	while True:
		floor = get_order()
		go_to_floor(floor)

