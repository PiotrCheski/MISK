import time
import threading
import os
from pathlib import Path
from coppeliasim_zmqremoteapi_client import RemoteAPIClient
from Code.create_areas import generate_areas
from Code.central import Centrala

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
    centrala = Centrala()

    # Start monitoring thread
    monitor_thread = threading.Thread(target=centrala.periodic_check)
    monitor_thread.start()

    try:
        while True:
            sim.step()  # triggers next simulation step (by defalt step is 0.05 seconds)
    except KeyboardInterrupt:
        print("[Main] Stopping...")
        centrala.stop()
        sim.stopSimulation()
        print("[Main] Simulation stopped.")

if __name__ == "__main__":
    main()
