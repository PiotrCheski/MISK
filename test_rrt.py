from Code.rrt_star import RRTStar
from Code.rrt_star_visualise import visualise_point, visualise_obstacles, visualise_path, remove_point, remove_obstacles, remove_path
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
    start = [-6.1, 6.1]
    goal = [0.1, -2.1]
    obstacles = [[-1.1, 0.1, 1.0], [-2.1, 2.1, 0.5] ]
    my_planer = RRTStar(start, goal, obstacles)
    my_planer.plan()
    print(my_planer.path_)

    print("[Main] Displaying path...")
    #getting handles so we can remove them later
    sh = visualise_point(sim, start, 0)
    gh = visualise_point(sim, goal, 1)
    oh = visualise_obstacles(sim, obstacles, 2)
    ph, lh = visualise_path(sim, my_planer.path_, 0)
    print("[Main] All visualised!")
    time.sleep(2)
    print("[Main] Now removing!")
    remove_point(sim, sh)
    remove_point(sim, gh)
    remove_obstacles(sim, oh)
    remove_path(sim, ph, lh)
    print("[Main] All clear!")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("[Main] Stopping...")
        sim.stopSimulation()
        print("[Main] Simulation stopped.")


if __name__ == "__main__":
    main()
