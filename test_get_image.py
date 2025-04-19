import cv2
import numpy as np
from Code.locate_marker import locate_marker
from coppeliasim_zmqremoteapi_client import RemoteAPIClient

"""
Testowanie pobierania obrazu z symulacji
"""

def main():
    client = RemoteAPIClient()
    sim = client.require('sim')

    print("[Main] Starting simulation...")
    sim.startSimulation() 

    # image needs to be from vision Sensor, not camera (camera image is not processable by api)
    visionSensorHandle = sim.getObject('/visionSensor')

    # Run a simulation in stepping mode:
    sim.setStepping(True)
    sim.startSimulation()

    while (t := sim.getSimulationTime()) < 20:
        img, [resX, resY] = sim.getVisionSensorImg(visionSensorHandle)
        img = np.frombuffer(img, dtype=np.uint8).reshape(resY, resX, 3)
        # In CoppeliaSim images are left to right (x-axis), and bottom to top (y-axis)
        # (consistent with the axes of vision sensors, pointing Z outwards, Y up)
        # and color format is RGB triplets, whereas OpenCV uses BGR:
        img = cv2.flip(cv2.cvtColor(img, cv2.COLOR_BGR2RGB), 0)
        new_img = locate_marker(img)

        cv2.imshow('', new_img)
        cv2.waitKey(1) # waits for click
        sim.step()  # triggers next simulation step

    print("[Main] Stopping...")
    sim.stopSimulation()
    print("[Main] Simulation stopped.")


if __name__ == "__main__":
    main()
