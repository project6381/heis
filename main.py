import panel
import elevator

def main():
	#floorDestination = int(raw_input("->"))


	while True:
		if panel.read_buttons() != None:
			(floor,button) = panel.read_buttons()			
			elevator.go_to_floor(floor)





if __name__ == "__main__":
    main()
