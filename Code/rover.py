from Code.rrt_star import RRTStar
from Code.sliding_solar_panel import retract_solar_panels, deploy_solar_panels
from Code.move_arm import deploy_arm, retract_arm, grip
from Code.move_rover_to_goal import move_rover_to_goal
from Code.rrt_star_visualise import visualise_path, remove_path
from Code.locate_marker import MarkerDetector
from Code.rover_mover import RoverMover
from Code.rover_state import RoverState, ActivityState
import cv2
import numpy as np
import random
import logging

class Rover:
    def __init__(self, sim, rover_name, centrala):
        self.sim = sim
        self.name = rover_name
        self.handle = sim.getObjectHandle(f'/{rover_name}')
        self.centrala = centrala
        self.task_queue = []
        self.position = self.get_position()
        self.planner = RRTStar(sim, [0,0], [0,0], [[0,0,0]])
        camera_name = f"/{rover_name}/Arm/Cuboid/Cylinder/visionSensor"
        self.camera_handle = sim.getObjectHandle(camera_name)
        self.detector = MarkerDetector(sim, self.camera_handle, self.handle)
        self.state = RoverState(self, rover_name)
        self.mover = RoverMover(sim, rover_name, [])

        self.discovered_markers = []
        self.replan_counter = 0
        # rejestracja w centrali
        self.centrala.register_rover(self.name, self, None, self.position)

    def tick(self):
        self.state.update()

        if self.state.is_forced_idle():
            return
        
        # 1. Jeśli IDLE — pobierz nowe zadanie
        if self.state.activity_state() == ActivityState.IDLE:
            task = self.centrala.request_new_task_for_rover(self.name)
            if task is None:
                logging.debug(f"[{self.name}] Brak nowych zadań.")
                return
            self.current_task = task

            if task['type'] == 'explore_point':
                self.goal = task['details']['target_coords_explore']
            else:
                self.goal = task['details']['target_coords']
                
            obstacles = self.find_obstacles(self.sim, self.goal)
            self.plan_new_path(self.goal, obstacles)
            self.state.set_activity_state(ActivityState.MOVING)
            logging.info(f"[{self.name}] Nowe zadanie: {task['type']} dla pola {task['field_name']}.")

            return
        # 2. Jeśli MOVING — wykonaj jazdę, popraw trasę co (X/20) sekund
        if self.state.activity_state() == ActivityState.MOVING:
            if self.mover.done:
                logging.info(f"[{self.name}] Reached goal.")
                self.state.set_activity_state(ActivityState.WORKING)
                return
            if self.replan_counter == 600:
                obstacles = self.find_obstacles(self.sim, self.goal)
                self.plan_new_path(self.goal, obstacles)
                self.replan_counter = 0
            self._move_rover()
            self.replan_counter += 1
            # gdy task exploracji to w trasie skanuj i dodaj do listy gdy wykryje nowy punkt wg id
            if self.current_task['type'] == 'explore_point':
                detected = self.detect_marker()
                if detected:
                    for point in detected:
                        if all(p[0] != point[0] for p in self.discovered_markers):
                            logging.info(f"[{self.name}] Znaleziono nowy id:{point[0]} na [{point[1]}, {point[2]}].")
                            self.discovered_markers.append(point)
            return
        # 3. Jeśli WORKING — wykonaj zadanie
        if self.state.activity_state() == ActivityState.WORKING:
            self.perform_task(self.current_task)
            self.centrala.report_task_completed(self.name, self.current_task['id'], "success")
            self.state.set_activity_state(ActivityState.IDLE)
            logging.info(f"[{self.name}] Zadanie ukończone, gotowy na nowe.")
            return

    def _move_rover(self):
        self.mover.step()

    # plan and move to goal
    def plan_new_path(self, goal, obstacles):
        self.find_path(goal, obstacles)
        # visualise_path(self.sim, self.planner.path_, random.randint(0,1000))
        self.mover.set_new_path(self.planner.path_)
        self.state.set_activity_state(ActivityState.MOVING)

    def detect_marker(self, visualise_image=False):
        self.sim.step()
        # matrix = markerdetector.get_camera_location()
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
                id = marker[0]
                #rvec = marker[1]
                tvec = marker[2]
                rotm = marker[3]
                marker_position, marker_orientation = self.detector.calculate_marker_location(tvec, rotm)
                # print(f"Found marker! \n at:{marker_position[0]},{marker_position[1]},{marker_position[2]}  \n with orientation:{marker_orientation[0]},{marker_orientation[1]},{marker_orientation[2]}")
                detected.append([id, marker_position[0], marker_position[1], 10])

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
        # if path empty then try 15 times with more steps
        i = 0
        while self.planner.path_ is None or i >15:
            self.planner.increase_iterations()
            self.planner.plan()
            i+=1
        # if still not path then there is none avalible, set you position as point
        if self.planner.path_ is None:
            self.planner.path_=[self.position]
            print("No path found, setting position as goal")


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

    def perform_task(self, task):
        # symulacja pracy — np. czasowa pauza, ruch ramienia, pomiar
        logging.info(f"[{self.name}] Wykonuję zadanie: {task['type']} na polu {task['field_name']}.")
        if task['type'] == "adjust_pH":
            self.centrala.fields[task['field_name']].pH = 7.0
            self.deploy_rover_arm()
            self.retract_rover_arm()
            print(f"Nowe pH w polu {task['field_name']}: {self.centrala.fields[task['field_name']].pH}")
        elif task['type'] == "restore_humidity":
            self.centrala.fields[task['field_name']].humidity = random.uniform(60, 75)
            self.deploy_rover_arm()
            self.retract_rover_arm()
            print(f"Nowa wilgotność w polu {task['field_name']}: {self.centrala.fields[task['field_name']].humidity}")
        elif task['type'] == 'explore_point':
            if self.discovered_markers:
                for point in self.discovered_markers:
                    marker_id = point[0]
                    position = [point[1], point[2], 15]
                    # na razie uproszczone
                    field_parameters_from_scan = {'humidity': 40}
                    self.centrala.report_discovered_field(self.name, marker_id, position, field_parameters_from_scan)
                # zgłoś i wyczyść
                logging.info(f"[{self.name}] Przesłano odkryte punkty w liczbie {len(self.discovered_markers)}, są nimi: {self.discovered_markers}")
                self.discovered_markers = []
        elif task['type'] == "visit_scan":
            pass
    
    def find_obstacles(self, sim, goal):
        obstacles = []
        centrala_handle = sim.getObject('/Centrala')
        position = sim.getObjectPosition(centrala_handle, -1)
        x, y = position[0], position[1]
        z = 0.5*1.5
        centrala_pos = [x, y, z]
        obstacles.append(centrala_pos)
        rover_x, rover_y, rover_z = self.get_position()
        margin = 0.25
        """
        i = 0
        while True:
                name = f'Plane[{i}]'
                try:
                    handle = sim.getObject(f'/{name}')
                except Exception:
                    break

                position = sim.getObjectPosition(handle, -1)
                x, y = position[0], position[1]

                if [x, y] != [goal[0], goal[1]] and (abs(x - rover_x) > margin or abs(y - rover_y) > margin):
                    obstacles.append((x, y, 1.0)) 
                i += 1
        """
        i = 0
        while True:
                name = f'Rock[{i}]'
                try:
                    handle = sim.getObject(f'/{name}')
                except Exception:
                    break

                position = sim.getObjectPosition(handle, -1)
                print(position)
                x, y = position[0], position[1]
                obstacles.append((x, y, 0.50)) 
                i += 1
        return obstacles 