import time
import numpy as np
import math
from coppeliasim_zmqremoteapi_client import RemoteAPIClient

def wrap_to_pi(angle):
    return (angle + np.pi) % (2 * np.pi) - np.pi

def move_rover_to_goal(goal, final_goal, steps=1, alpha=1.0, pause_time=0.0):
    """
    Przesuwa łazik ('/Chassis') w kierunku goal w zadanej liczbie kroków,
    z płynną interpolacją pozycji i obrotu.

    :param steps: Liczba kroków interpolacji (więcej = płynniej)
    :param alpha: Współczynnik gładkości interpolacji kąta yaw (0.001–0.01)
    :param pause_time: Czas pauzy między krokami (dla efektu wizualnego)
    """
    goal.append(0)
    client = RemoteAPIClient()
    sim = client.require('sim')

    rover_handle = sim.getObject('/Chassis')

    start_pos = sim.getObjectPosition(rover_handle, -1)
    end_pos = goal
    print(end_pos)
    z = start_pos[2]  # wysokość zostaje stała


    for i in range(steps + 1):
        t = i / steps
        x = start_pos[0] + t * (end_pos[0] - start_pos[0])
        y = start_pos[1] + t * (end_pos[1] - start_pos[1])

        sim.setObjectPosition(rover_handle, -1, [x, y, z])

        # Oblicz orientację
        dx = goal[0] - x
        dy = goal[1] - y
        target_yaw = wrap_to_pi(np.arctan2(dy, dx))
        current_yaw = wrap_to_pi(sim.getObjectOrientation(rover_handle, -1)[2])
        interpolated_yaw = wrap_to_pi((1 - alpha) * current_yaw + alpha * target_yaw)

        sim.setObjectOrientation(rover_handle, -1, [0, 0, interpolated_yaw])

        if pause_time > 0:
            time.sleep(pause_time)
