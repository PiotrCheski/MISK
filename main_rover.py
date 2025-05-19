import time
import threading
import os
from pathlib import Path
from coppeliasim_zmqremoteapi_client import RemoteAPIClient
from Code.central import Centrala
from Code.rover import Rover
from Code.rrt_star_visualise import visualise_point

def main():
    client = RemoteAPIClient()
    sim = client.require('sim')

    sim.setStepping(True) # in discrete mode, not countinous time (cameras will not work with api)
    sim.startSimulation()

    print("[Main] Starting Centrala...")
    centrala = Centrala(client)

    # Podpięcie łazików, jakiś for będzie trzeba zrobić
    name = 'Chassis'
    rover_id1 = Rover(sim, name, centrala)
    name2 = 'Chassis[1]'
    rover_id2 = Rover(sim, name2, centrala)

    #punkty = rover_idx.detect_marker()
    #for punkt in punkty:
    #    visualise_point(sim, punkt, 0)
    #    print(punkt)
  
    #rover_idx.deploy_rover_panel()
    #rover_idx.retract_rover_panel()
    #rover_idx.deploy_rover_arm()
    #rover_idx.retract_rover_arm()
    rovers = [rover_id1, rover_id2]
    rover_id1.plan_new_path([-2.0, -2.0], [[-1.1, 0.1, 1.0], [-2.1, 2.1, 0.5] ])
    rover_id2.plan_new_path([-2.0, -2.0], [[-1.1, 0.1, 1.0], [-2.1, 2.1, 0.5] ])

    # Start monitoring thread
    # monitor_thread = threading.Thread(target=centrala.periodic_check)
    # monitor_thread.start()

    try:
        while True:

            for rover in rovers:
                if rover.mover.done is not True:
                    rover.move_rover()

            sim.step()  # triggers next simulation step (by defalt step is 0.05 seconds)
    except KeyboardInterrupt:
        print("[Main] Stopping...")
        centrala.stop()
        sim.stopSimulation()
        print("[Main] Simulation stopped.")

if __name__ == "__main__":
    main()
