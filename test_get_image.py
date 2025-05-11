import cv2
import numpy as np
from Code.locate_marker import MarkerDetector
from coppeliasim_zmqremoteapi_client import RemoteAPIClient

"""
Testowanie detekcji i lokalizaji markerów aruco
"""

def main():
    client = RemoteAPIClient()
    sim = client.require('sim')
    print("[Main] Starting simulation...")
    sim.setStepping(True) # (by defalt step is 0.05 seconds)
    sim.startSimulation() 

    # image needs to be from vision sensor (camera image is not processable by api)
    vision_sensor_handle = sim.getObject('/visionSensor')
    rover_handle = sim.getObject('/Chassis')
    MarkerDetector = MarkerDetector(sim, vision_sensor_handle, rover_handle)

    try:
        while True:
            # get image
            img, [resX, resY] = sim.getVisionSensorImg(vision_sensor_handle)
            img = np.frombuffer(img, dtype=np.uint8).reshape(resY, resX, 3)
            img = cv2.flip(cv2.cvtColor(img, cv2.COLOR_BGR2RGB), 0)
            # find markers
            new_img, markers = MarkerDetector.locate_marker(img)
            # there are markers then locate then
            if markers:
                for marker in markers:
                    tvec = marker[2]
                    rotm = marker[3]
                    marker_position, marker_orientation = MarkerDetector.calculate_marker_location(tvec, rotm)
                    print(f"Found marker! \n at:{marker_position[0]},{marker_position[1]},{marker_position[2]}  \n with orientation:{marker_orientation[0]},{marker_orientation[1]},{marker_orientation[2]}")
            sim.step()

    except KeyboardInterrupt:
        print("[Main] Stopping...")
        sim.stopSimulation()
        print("[Main] Simulation stopped.")


if __name__ == "__main__":
    main()
