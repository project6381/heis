import channels as channel
import constants as const
import io as ioLib


class ElevatorInterface:
    io = ioLib.ioInterface()

    def set_motor_direction(self, dirn):
        if dirn == 1:
            self.io.write_analog(channel.MOTOR, 0)
        elif dirn > 1:
            self.io.clear_bit(channel.MOTORDIR)
            self.io.write_analog(channel.MOTOR, const.MOTOR_SPEED)
        else:
            self.io.set_bit(channel.MOTORDIR)
            self.io.write_analog(channel.MOTOR, const.MOTOR_SPEED)

    def get_floor_sensor_signal(self):
        if self.io.read_bit(channel.SENSOR_FLOOR1) == 1:
            return 0
        elif self.io.read_bit(channel.SENSOR_FLOOR2) == 1:
            return 1
        elif self.io.read_bit(channel.SENSOR_FLOOR3) == 1:
            return 2
        elif self.io.read_bit(channel.SENSOR_FLOOR4) == 1:
            return 3
        else:
            return -1

    def __init__(self):
        init_success = self.io.init()
        assert init_success, "Unable to initialize elevator hardware!"
