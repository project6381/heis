### io.py ###

import comedi as c
import channels as channel
import ctypes

class ioInterface:
	c_con = None

	def init(self):
		self.c_con = c.comedi_open('/dev/comedi0')

		if self.c_con == None:
			return 0

		status = 0
		for i in range(8):
			status |= c.dio_config(self.c_con, channel.PORT_1_SUBDEVICE, i + channel.PORT_1_CHANNEL_OFFSET, channel.PORT_1_DIRECTION)
	    	status |= c.dio_config(self.c_con, channel.PORT_2_SUBDEVICE, i + channel.PORT_2_CHANNEL_OFFSET, channel.PORT_2_DIRECTION)
	    	status |= c.dio_config(self.c_con, channel.PORT_3_SUBDEVICE, i + channel.PORT_3_CHANNEL_OFFSET, channel.PORT_3_DIRECTION)
	    	status |= c.dio_config(self.c_con, channel.PORT_4_SUBDEVICE, i + channel.PORT_4_CHANNEL_OFFSET, channel.PORT_4_DIRECTION)
	    
		return status == 0

	def set_bit(self, bchannel):
		arg1 = ctypes.c_uint32(bchannel >> 8).value
		arg2 = ctypes.c_uint32(bchannel & 0xff).value
		arg3 = ctypes.c_uint32(1).value
		c.dio_write(self.c_con, arg1, arg2, arg3)

	def clear_bit(self, bchannel):
		arg1 = ctypes.c_uint32(bchannel >> 8).value
		arg2 = ctypes.c_uint32(bchannel & 0xff).value
		arg3 = ctypes.c_uint32(0).value
		c.dio_write(self.c_con, arg1, arg2, arg3)

	def read_bit(self, bchannel):
		arg1 = ctypes.c_uint32(bchannel >> 8).value
		arg2 = ctypes.c_uint32(bchannel & 0xff).value
		retValue = c.dio_read(self.c_con, arg1, arg2)
		return retValue[1]

	def write_analog(self, bchannel, bvalue):
		arg1 = ctypes.c_uint32(bchannel >> 8).value
		arg2 = ctypes.c_uint32(bchannel & 0xff).value
		arg3 = ctypes.c_uint32(0).value
		bvalue = ctypes.c_uint32(bvalue).value
		c.data_write(self.c_con, arg1, arg2, arg3, c.AREF_GROUND, bvalue)

	def read_analog(self, bchannel):
		arg1 = ctypes.c_uint32(bchannel >> 8).value
		arg2 = ctypes.c_uint32(bchannel & 0xff).value
		arg3 = ctypes.c_uint32(0).value
		return c.data_read(self.c_con, arg1, arg2, arg3, c.AREF_GROUND)
