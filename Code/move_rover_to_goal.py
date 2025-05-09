import time
import numpy as np
import math
from coppeliasim_zmqremoteapi_client import RemoteAPIClient

def wrap_to_pi(angle):
    return (angle + np.pi) % (2 * np.pi) - np.pi

def move_rover_to_goal(goal, final_goal, dt=0.05, alpha=1.0, pause_time=0.0):
    """
    Przesuwa łazik ('/Chassis') w kierunku goal w zadanej liczbie kroków,
    z płynną interpolacją pozycji i obrotu.

    :param dt: Liczba kroków interpolacji (więcej = płynniej)
    :param alpha: Współczynnik gładkości interpolacji kąta yaw (0.001–0.01)
    :param pause_time: Czas pauzy między krokami (dla efektu wizualnego)
    """
    goal.append(0)
    client = RemoteAPIClient()
    sim = client.require('sim')

    rover_handle = sim.getObject('/Chassis')

    start_pos = sim.getObjectPosition(rover_handle, -1)
    end_pos = goal

    v = 0.5 # m/s
    dist = math.sqrt( math.pow((end_pos[0] - start_pos[0]),2) + math.pow((end_pos[1] - start_pos[1]),2) )
    time = dist/v
    steps = max(math.ceil(time/dt),1)

    print(end_pos)
    x = start_pos[0]
    y = start_pos[1]
    z = start_pos[2]  # wysokość zostaje stała

    for i in range(steps + 1):
        #t = i/steps
        dx = goal[0] - x
        dy = goal[1] - y
        distance = math.hypot(dx, dy)
        # Przerwij jeśli osiągnięto cel
        if distance < 0.05:
            break

        # Oblicz orientację -> poprawiona o 180 bo łazik na -x z przodu
        target_yaw = wrap_to_pi(np.arctan2(dy, dx))
        current_yaw = wrap_to_pi(sim.getObjectOrientation(rover_handle, -1)[2])
        interpolated_yaw = wrap_to_pi((1 - alpha) * current_yaw + alpha * target_yaw)
        sim.setObjectOrientation(rover_handle, -1, [0, 0, interpolated_yaw + math.pi])

        # oblicz pozycję
        #target_yaw = wrap_to_pi(np.arctan2(dy, dx))
        x = x + dt * v * math.cos(target_yaw)
        y = y + dt * v * math.sin(target_yaw)
        sim.setObjectPosition(rover_handle, -1, [x, y, z])

        if pause_time > 0:
            time.sleep(pause_time)
