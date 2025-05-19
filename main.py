import time
import random
import threading
import os
from pathlib import Path
from coppeliasim_zmqremoteapi_client import RemoteAPIClient
from Code.central import Centrala
from Code.rover import Rover
from Code.move_rover_to_goal import move_rover_to_goal

def main():
    client = RemoteAPIClient()
    sim = client.require('sim')

    #print("[Main] Loading Mars terrain scene...")
    #
    #current_dir = os.path.dirname(os.path.abspath(__file__))
    #scene_path = os.path.join(current_dir, "mars_terrain.ttt")
    #
   ## sim.loadScene(scene_path)
    #print("[Main] Scene loaded.")
#
    #print("[Main] Generating areas...")
    #generate_areas()  # This will create fields
#
    #print("[Main] Starting simulation...")

    sim.setStepping(True) # in discrete mode, not countinous time (cameras will not work with api)
    sim.startSimulation()

    print("[Main] Starting Centrala...")
    centrala = Centrala(client)

    rover_names = ['Rover0', 'Rover1']
    rover0 = Rover(sim, rover_names[0], centrala)
    rover1 = Rover(sim, rover_names[1], centrala)

    rover_handle0 = sim.getObject("/" + rover_names[0])
    rover_handle1 = sim.getObject("/" + rover_names[1])

    task0 = centrala.request_new_task_for_rover(rover_names[0])
    task1 = centrala.request_new_task_for_rover(rover_names[1])

    obstacles = []
    rover0.plan_new_path(task0['target_coords'], obstacles)
    rover1.plan_new_path(task1['target_coords'], obstacles)
    
    rover_names_list = [rover0, rover1]
    try:
        while True:
            for rover in rover_names_list:
                if rover.mover.done is not True:
                    rover.move_rover()
            sim.step()
    #while True:
    #    task = centrala.request_new_task_for_rover(rover_names[0])
    #    
    #    if task is None:
    #        print("Brak nowych zadań. Czekam...")
    #        time.sleep(1)  # odczekaj sekundę i spróbuj ponownie
    #        continue
#
    #    goal = task['target_coords']
    #    print(f"Nowe zadanie: {task['type']} w polu {task['field_name']}, cel: {goal}")
#
    #    obstacles = []
    #    
    #    rover.move_to_goal(goal, obstacles) 
#
    #    final_position = sim.getObjectPosition(rover_handle, -1)
    #    if abs(final_position[0] - goal[0]) <= 0.5 and abs(final_position[1] - goal[1]) <= 0.5:
    #        print("Rover reached the goal!")
    #        # TUTAJ URUCHAMIA RAMIĘ
    #        if task['type'] == "adjust_pH":
    #            centrala.fields[task['field_name']].pH = 7.0
    #            rover.deploy_rover_arm()
    #            rover.retract_rover_arm()
    #            print(f"Nowe pH w polu {task['field_name']}: {centrala.fields[task['field_name']].pH}")
    #        elif task['type'] == "restore_humidity":
    #            centrala.fields[task['field_name']].humidity = random.uniform(60, 75)
    #            rover.deploy_rover_arm()
    #            rover.retract_rover_arm()
    #            print(f"Nowa wilgotność w polu {task['field_name']}: {centrala.fields[task['field_name']].humidity}")
    #        elif task['type'] == "visit_scan":
    #            # tu możesz dodać logikę dla visit_scan
    #            pass
    #        centrala.report_task_completed(rover_names[0], task['id'], "success")
    #    else:
    #        print("Rover nie dotarł do celu, zadanie nie zostało ukończone.")
    #        centrala.report_task_completed(rover_names[0], task['id'], "failed")
#
    #    sim.step()
    #rover.move_to_goal([4.0, 4.0], obstacles) 

    # Start monitoring thread
    # monitor_thread = threading.Thread(target=centrala.periodic_check)
    # monitor_thread.start()

    #try:
    #    while True:
    #        sim.step()  # triggers next simulation step (by defalt step is 0.05 seconds)
    except KeyboardInterrupt:
        print("[Main] Stopping...")
        centrala.stop()
        sim.stopSimulation()
        print("[Main] Simulation stopped.")

if __name__ == "__main__":
    main()
