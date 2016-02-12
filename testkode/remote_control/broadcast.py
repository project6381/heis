from socket import *

def recieve():
	recieve = ('', 17852)
	udp = socket(AF_INET, SOCK_DGRAM)
	udp.bind(recieve)
	udp.setsockopt(SOL_SOCKET, SO_BROADCAST, 1)
	data, address = udp.recvfrom(1024)
	udp.close()
	return(errorcheck(data))

def send(data):
	send = ('<broadcast>', 17852)
	udp = socket(AF_INET, SOCK_DGRAM)
	udp.setsockopt(SOL_SOCKET, SO_BROADCAST, 1)
	message='<%s;%s>' % (str(len(data)), data)
	udp.sendto(message, send)
	udp.close()

def errorcheck(data):
	if data[0]=='<' and data[len(data)-1]=='>':

		counter=1
		separator=False
		separator_pos=0
		for char in data:
			if char == ";" and separator==False:
				separator_pos=counter
				separator=True
			counter+=1

		message_length=str(len(data)-separator_pos-1)
		test_length=str()
		for n in range(1,separator_pos-1):
			test_length+=data[n]

		if test_length==message_length and separator==True:
			message=str()
			for n in range(separator_pos,len(data)-1):
				message+=data[n]
			return message
		else:
			return None
	else:
		return None

