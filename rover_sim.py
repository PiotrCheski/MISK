import time
import numpy as np
from coppeliasim_zmqremoteapi_client import RemoteAPIClient

client = RemoteAPIClient()
sim = client.getObject('sim')

# Pobierz uchwyt do sześcianu (łazika)
rover_handle = sim.getObject('/Chassis')
goal_handle = sim.getObject('/dummy')

# Parametry ruchu
start_pos = sim.getObjectPosition(rover_handle, -1)
end_pos = sim.getObjectPosition(goal_handle, -1)
steps = 1000
sim.startSimulation()

for i in range(steps + 1):
    t = i / steps
    x = start_pos[0] + t * (end_pos[0] - start_pos[0])
    y = start_pos[1] + t * (end_pos[1] - start_pos[1])
    z = start_pos[2]
    sim.setObjectPosition(rover_handle, -1, [x, y, z])

    # Oblicz docelowy kąt
    dx = end_pos[0] - x
    dy = end_pos[1] - y
    target_yaw = np.arctan2(dy, dx) + np.pi

    # Pobierz aktualny kąt
    current_yaw = sim.getObjectOrientation(rover_handle, -1)[2]

    # Zawijanie kąta do [-π, π]
    def wrap_to_pi(angle):
        return (angle + np.pi) % (2 * np.pi) - np.pi

    target_yaw = wrap_to_pi(target_yaw)
    current_yaw = wrap_to_pi(current_yaw)

    # Interpolacja kąta
    alpha = 0.005
    interpolated_yaw = wrap_to_pi((1 - alpha) * current_yaw + alpha * target_yaw)

    # Ustawienie nowej orientacji
    sim.setObjectOrientation(rover_handle, -1, [0, 0, interpolated_yaw])


    # time.sleep(0.001)  # można odkomentować dla wizualnego efektu
