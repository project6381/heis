import broadcast
import struct
import sys

while True:
	
	print >>sys.stderr, '\nwaiting to receive message'
	data = broadcast.recieve();

	print >>sys.stderr, 'received %s' % (data)
