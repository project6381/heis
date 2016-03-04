#from class_panel import Panel
from class_broadcast import Broadcast 
#import elevator
import time

def main():
	#floorDestination = int(raw_input("->"))

	

	#panel1 = Panel()
	#panel1.read_pressed_button()
	broadcast1 = Broadcast()

	print broadcast1.read_message()

	time.sleep(1)

	broadcast1.send('hei, dette er heis1')
	broadcast1.send('heis1 er sulten')

	

	time.sleep(1)
	print broadcast1.read_message()
	print broadcast1.read_message()

if __name__ == "__main__":
    main()