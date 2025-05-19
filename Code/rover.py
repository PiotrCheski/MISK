from Code.rrt_star import RRTStar
from Code.sliding_solar_panel import retract_solar_panels, deploy_solar_panels
from Code.move_arm import deploy_arm, retract_arm, grip
from Code.move_rover_to_goal import move_rover_to_goal
from Code.rrt_star_visualise import visualise_path, remove_path
from Code.locate_marker import MarkerDetector
from Code.rover_mover import RoverMover
import cv2
import numpy as np
import random

class Rover:
    def __init__(self, sim, rover_name, centrala):
        self.sim = sim
        self.name = rover_name
        self.handle = sim.getObjectHandle(f'/{rover_name}')
        self.central = centrala
        self.task_queue = []
        self.position = self.get_position()
        self.planner = RRTStar(sim, [0,0], [0,0], [[0,0,0]])
        camera_name = f"/{rover_name}/Arm/Cuboid/Cylinder/visionSensor"
        self.camera_handle = sim.getObjectHandle(camera_name)
        self.detector = MarkerDetector(sim, self.camera_handle, self.handle)
        self.mover = RoverMover(sim, rover_name, [])
        
        # rejestracja w centrali
        self.central.register_rover(self.name, self, None, self.position)

    def move_rover(self):
        self.mover.step()
    
    # plan and move to goal
    def plan_new_path(self, goal, obstacles):    
        self.find_path(goal, obstacles)
        self.mover.set_new_path(self.planner.path_)

    def detect_marker(self, visualise_image=False):
        self.sim.step()
        #matrix = markerdetector.get_camera_location()
        # get image
        img, [resX, resY] = self.sim.getVisionSensorImg(self.camera_handle)
        img = np.frombuffer(img, dtype=np.uint8).reshape(resY, resX, 3)
        img = cv2.flip(cv2.cvtColor(img, cv2.COLOR_BGR2RGB), 0)
        # find markers
        detected = []
        new_img, markers = self.detector.locate_marker(img, visualise_image)
        # there are markers then locate then
        if markers:
            for marker in markers:
                tvec = marker[2]
                rotm = marker[3]
                marker_position, marker_orientation = self.detector.calculate_marker_location(tvec, rotm)
                #print(f"Found marker! \n at:{marker_position[0]},{marker_position[1]},{marker_position[2]}  \n with orientation:{marker_orientation[0]},{marker_orientation[1]},{marker_orientation[2]}")
                detected.append([marker_position[0], marker_position[1], 10])
        return detected
    
    # return position
    def get_position(self):
        pos = self.sim.getObjectPosition(self.handle, -1)
        return pos  # np. [x, y, z]
    
    # use planner to find path
    def find_path(self, goal, obstacles):
        # update map state
        self.planner.update_state(self.get_position(), goal, obstacles)
        # get path
        self.planner.plan()
        # if path empty then try 10 times
        i = 0
        while self.planner.path_ is None or i >10:
            self.planner.increase_iterations()
            self.planner.plan()
            i+=1
        # if still not path then there is none avalible, set you position as point
        if self.planner.path_ is None:
            self.planner.path_=[self.position]

    # solar panel deployment
    def deploy_rover_panel(self):
        deploy_solar_panels(self.sim, self.name)

    # solar panel retraction
    def retract_rover_panel(self):
        retract_solar_panels(self.sim, self.name)

    # arm deployment
    def deploy_rover_arm(self):
        deploy_arm(self.sim, self.name)
        grip(self.sim, self.name, 0.5)

    # arm retraction
    def retract_rover_arm(self):
        retract_arm(self.sim, self.name)
        grip(self.sim, self.name, 1.0)
    
    # todo: bateria

