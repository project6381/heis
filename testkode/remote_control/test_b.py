import broadcast

message = raw_input("->")
while message != 'q':
	broadcast.send(message)
	message = raw_input("->")



