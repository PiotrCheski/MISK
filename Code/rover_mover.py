import math
import numpy as np
import logging

class RoverMover:
    def __init__(self, sim, name, path, v=0.1, alpha=0.1):
        self.sim = sim
        self.name = name
        self.path = path
        self.v = v
        self.alpha = alpha
        self.goal_index = 0
        self.done = False

        self.handle = sim.getObject(f'/{name}')
        self.dt = sim.getSimulationTimeStep()
        self.pos = sim.getObjectPosition(self.handle, -1)
        self.z = self.pos[2]

    def step(self):
        self.pos = self.sim.getObjectPosition(self.handle, -1)
        if self.done or self.goal_index >= len(self.path):
            if not self.done:
                logging.info(f"[{self.name}] Reached goal.")
            self.done = True
            return

        goal = self.path[self.goal_index][:2]  # X, Y
        dx = goal[0] - self.pos[0]
        dy = goal[1] - self.pos[1]
        distance = math.hypot(dx, dy)

        if distance < 0.05:
            self.goal_index += 1
            return

        # Orientacja
        target_yaw = self.wrap_to_pi(np.arctan2(dy, dx))
        current_yaw =  self.wrap_to_pi(self.sim.getObjectOrientation(self.handle, -1)[2])
        interpolated_yaw =  self.wrap_to_pi((1 - self.alpha) * current_yaw + self.alpha * target_yaw)
        self.sim.setObjectOrientation(self.handle, -1, [0, 0, interpolated_yaw])

        # Pozycja
        x = self.pos[0] + self.dt * self.v * math.cos(target_yaw)
        y = self.pos[1] + self.dt * self.v * math.sin(target_yaw)
        self.pos = [x, y, self.z]
        self.sim.setObjectPosition(self.handle, -1, self.pos)

    def wrap_to_pi(self, angle):
        return (angle + np.pi) % (2 * np.pi) - np.pi

    def set_new_path(self, path):
        self.path = path
        self.goal_index = 0
        self.done = False
