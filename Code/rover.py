class Rover:
    def __init__(self, sim, rover_name, centrala):
        self.sim = sim
        self.name = rover_name
        self.handle = sim.getObjectHandle(rover_name)
        self.central = centrala
        self.task_queue = []
        self.position = self.get_position()
        
        # rejestracja w centrali
        self.central.register_rover(self.name, self, None, self.position)

    def get_position(self):
        pos = self.sim.getObjectPosition(self.handle, -1)
        return pos  # np. [x, y, z]
