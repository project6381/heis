from socket import socket, AF_INET, SOCK_DGRAM, SOL_SOCKET, SO_BROADCAST


class Receiver(object):
	
	def __init__(self, port):
		self.__bind_port = ('', port)
		self.__udp = socket(AF_INET, SOCK_DGRAM)
		self.__udp.setsockopt(SOL_SOCKET, SO_BROADCAST, 1)
		self.__udp.bind(self.__bind_port)

	def wait_for_and_receive_broadcast(self):
		data, address = self.__udp.recvfrom(1024)
		return self.__errorcheck_and_remove_formatting(data)

	def __errorcheck_and_remove_formatting(self,data):
		###### CHECKS THAT THE MESSAGE HAS THE FORMAT '<provided_message_length;message>' ######
		if (data[0] == '<') and (data[len(data) -1] == '>'):
			character_counter = 1
			separator_found = False
			separator_position = 0

			for character in data:
				if (character == ";") and (separator_found == False):
					separator_position = character_counter
					separator_found = True
				character_counter += 1

			measured_message_length = str(len(data) - separator_position - 1)
			provided_message_length = str()

			for character in range(1, separator_position - 1):
				provided_message_length += data[character]

			if (provided_message_length == measured_message_length) and (separator_found == True):
				message = str()
				for character in range(separator_position,len(data) - 1):
					message += data[character]
				return message
			else:
				return None
		else:
			return None

class Broadcaster(object):

	def __init__(self, port):
		self.__send_flags = ('<broadcast>', port)

	def broadcast(self, data):
		broadcast_data = self.__format_data_for_errorchecking(data)

		with BroadcastSocketUDP() as udp:
			udp.sendto(broadcast_data, self.__send_flags)

	def __format_data_for_errorchecking(self, data):
		###### MESSAGE IN FORMAT '<message_length;message>' FOR ERRORCHECK ######
		return '<%s;%s>' % (str(len(data)), data)

class BroadcastSocketUDP(object):
	
	def __init__(self):
		self.udp = socket(AF_INET, SOCK_DGRAM)
		self.udp.setsockopt(SOL_SOCKET, SO_BROADCAST, 1)

	def __enter__(self):
		return self.udp

	def __exit__(self, type, value, traceback):
		self.udp.close()

class ReceiverSocketUDP(object):

	def __init__(self, port):
		self.__bind_port = ('', port)
		self.__udp = socket(AF_INET, SOCK_DGRAM)
		self.__udp.bind(self.__bind_port)
		self.__udp.setsockopt(SOL_SOCKET, SO_BROADCAST, 1)
		
	def __enter__(self):
		return self.__udp

	def __exit__(self, type, value, traceback):
		self.__udp.close()