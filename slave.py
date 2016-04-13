import time

from config_parameters import MY_ID, TICK, N_ELEVATORS
from message_handler import MessageHandler
from slave_driver import SlaveDriver


def main():
    # try:
    message_handler = MessageHandler()
    slave_driver = SlaveDriver()

    while True:
        time.sleep(TICK * N_ELEVATORS)

        position = slave_driver.elevator_position()
        master_message = message_handler.receive_from_master()

        if message_handler.no_active_master():
            slave_driver.set_offline_mode(True)
        else:
            slave_driver.set_offline_mode(False)

        if master_message is not None:
            print master_message['master_id']
            if slave_driver.changing_master(master_message):
                # print 'pikk'

                ###### SENDS UNFINISHED ORDERS AS BUTTON PRESSES ######
                (unfinished_orders_up, unfinished_orders_down) = slave_driver.unfinished_orders()
                message_handler.send_to_master(unfinished_orders_up, unfinished_orders_down, MY_ID, position[0],
                                               position[1], position[2])

            else:
                slave_driver.update_master_orders(master_message['orders_up'][:], master_message['orders_down'][:])

                (buttons_up, buttons_down) = slave_driver.external_buttons_pressed()

                if not slave_driver.move_timeout():
                    message_handler.send_to_master(buttons_up, buttons_down, MY_ID, position[0], position[1],
                                                   position[2])



                ###### ALL THREADS MAY INTERRUPT MAIN USING A KEYBOARD INTERRUPT EXCEPTION ######
                # except KeyboardInterrupt:
                #	pass
                #
                # except StandardError as error:
                #	print error
                # finally:
                #	print "Exiting slave.py..."


if __name__ == "__main__":
    main()
