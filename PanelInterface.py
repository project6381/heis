import io as ioLib
import channels as channel
import constants as const





class PanelInterface:
	
	io = ioLib.ioInterface()
	
	def set_button_lamp(self, button, floor, value):
		assert floor >= 0 and floor < const.N_FLOORS, "set_button_lamp: 0 <= floor < N_FLOORS"
		assert button >= 0 and button < const.N_BUTTONS, "set_button_lamp: 0 <= button < N_BUTTONS"

		if value:
			self.io.set_bit(channel.lamp_channel_matrix[floor][button])
		else:
			self.io.clear_bit(channel.lamp_channel_matrix[floor][button])

	def set_floor_indicator(self, floor):
		assert floor >= 0 and floor < const.N_FLOORS, "set_floor_indicator: 0 <= floor < N_FLOORS"

		if floor & 0x02:
			self.io.set_bit(channel.LIGHT_FLOOR_IND1)
		else:
			self.io.clear_bit(channel.LIGHT_FLOOR_IND1)

		if floor & 0x01:
			self.io.set_bit(channel.LIGHT_FLOOR_IND2)
		else:
			self.io.clear_bit(channel.LIGHT_FLOOR_IND2)


	def set_door_open_lamp(self, value):
		if value:
			self.io.set_bit(channel.LIGHT_DOOR_OPEN)
		else:
			self.io.clear_bit(channel.LIGHT_DOOR_OPEN)

	def set_stop_lamp(self, value):
		if value:
			self.io.set_bit(channel.LIGHT_STOP)
		else:
			self.io.clear_bit(channel.LIGHT_STOP)

	def get_button_signal(self, button, floor):
		assert floor >= 0 and floor < const.N_FLOORS, "set_button_lamp: 0 <= floor < N_FLOORS"
		assert button >= 0 and button < const.N_BUTTONS, "set_button_lamp: 0 <= button < N_BUTTONS"

		if self.io.read_bit(channel.button_channel_matrix[floor][button]) > 0:
			return 1
		else:
			return 0

	def get_stop_signal(self):
		return self.io.read_bit(channel.STOP)

	def get_obstruction_signal(self):
		return self.io.read_bit(channel.OBSTRUCTION)

	def __init__(self):
		init_success = self.io.init()
		assert init_success, "Unable to initialize elevator hardware!"

		for f in range(const.N_FLOORS):
			for bt in range(const.N_BUTTONS):
				self.set_button_lamp(bt, f, 0)

		self.set_stop_lamp(0)
		self.set_door_open_lamp(0)
		self.set_floor_indicator(0)


