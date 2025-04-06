from Code.rrt_star import RRTStar
from Code.rrt_star_visualise import visualise_point, visualise_obstacles, visualise_path, remove_point, remove_path
from coppeliasim_zmqremoteapi_client import RemoteAPIClient
import time

"""
Testowanie RRT* i jego wizualizacji
"""

def main():
    client = RemoteAPIClient()
    sim = client.require('sim')

    print("[Main] Starting simulation...")
    sim.startSimulation() 

    print("[Main] Calculating path...")
    start = [0.1, 0.1]
    goal = [6.1, 6.1]
    obstacles = [[3.1, 3.1, 1.0] ]
    my_planer = RRTStar(start, goal, obstacles)
    my_planer.plan()
    print(my_planer.path_)

    print("[Main] Displaying path...")
    visualise_path(sim, my_planer.path_, 0)
    visualise_point(sim, start, 0)
    visualise_point(sim, goal, 1)
    visualise_obstacles(sim, obstacles, 2)
    print("[Main] All visualised!")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("[Main] Stopping...")
        sim.stopSimulation()
        print("[Main] Simulation stopped.")


if __name__ == "__main__":
    main()
