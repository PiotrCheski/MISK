import time
import random
import threading
import os
import logging
from pathlib import Path
from coppeliasim_zmqremoteapi_client import RemoteAPIClient
from Code.central import Centrala
from Code.rover import Rover
from Code.move_rover_to_goal import move_rover_to_goal
from Code.duplicate_rover import duplicate_rover

def main():
    logging.basicConfig(
        level=logging.INFO,
        format="[%(asctime)s] [%(filename)s] %(message)s",
        datefmt="%H:%M:%S",
    )

    client = RemoteAPIClient()
    sim = client.require('sim')

    sim.setStepping(True)
    sim.startSimulation()

    print("[Main] Starting Centrala...")
    centrala = Centrala(client)

    num_rovers = 3

    sim_object_names = [f"Rover{i}" for i in range(num_rovers)]

    rover_name = "/Rover0"
    rover_handle = sim.getObject(rover_name)
    position = sim.getObjectPosition(rover_handle, -1)
    pos_x, pos_y = -4, -4
    for i in range(1, num_rovers):
        duplicate_rover(sim, rover_name, sim_object_names[i], pos_x, pos_y+i, pos_z=0.375)

    rover_names_list = [Rover(sim, sim_object_names[i], centrala)
                        for i in range(num_rovers)]
    print(rover_names_list)
    start_time = time.time()
    rover_removed = False

    try:
        while True:
            current_time = time.time()
            elapsed_time = current_time - start_time

            # Usunięcie Rover0 po 30 sekundach czasu rzeczywistego
            if not rover_removed and elapsed_time >= 900:
                rover_names_list.pop(0)  # Usuwa Rover0 z listy
                rover_removed = True
                print("[Main] Rover0 removed after 30 seconds of real time.")

            for rover in rover_names_list:
                rover.tick()
            sim.step()

    except KeyboardInterrupt:
        print("[Main] Stopping...")
        centrala.stop()
        sim.stopSimulation()
        print("[Main] Simulation stopped.")

if __name__ == "__main__":
    main()
