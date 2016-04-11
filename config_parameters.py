#### Constants ####
# Computer ID #
MY_ID = 2

# Number of elevators
N_ELEVATORS = 3

#PORTS
MASTER_TO_SLAVE_PORT = 17852
SLAVE_TO_MASTER_PORT = 17853
MASTER_TO_MASTER_PORT = 17854
SLAVE_TO_SLAVE_PORT = 17855
MASTER_BUTTON_ORDERS_PORT = 17856 

#### Performance parameters ####

# System "tick" -- delay for time.sleep()
TICK = 0.001 

# Downtime for network operations -- to limit use of bandwidth
NET_WAIT = TICK*10

# Timeout limits
SLAVE_TIMEOUT = 1
MASTER_TIMEOUT = 2
ORDER_ID_TIMEOUT = 2
