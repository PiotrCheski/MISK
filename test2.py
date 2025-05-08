import time
import numpy as np
from coppeliasim_zmqremoteapi_client import RemoteAPIClient

client = RemoteAPIClient()
sim = client.getObject('sim')

# Pobierz uchwyt do sześcianu
rover_handle = sim.getObject('/rover')

# Parametry ruchu
start_pos = sim.getObjectPosition(rover_handle, -1)
end_pos = [1, 0, 0.1]
duration = 5  # sekundy
steps = 100

for i in range(steps + 1):
    t = i / steps
    x = start_pos[0] + t * (end_pos[0] - start_pos[0])
    y = start_pos[1] + t * (end_pos[1] - start_pos[1])
    z = start_pos[2]
    sim.setObjectPosition(rover_handle, -1, [x, y, z])
    time.sleep(duration / steps)
