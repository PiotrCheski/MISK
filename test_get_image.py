import cv2
import numpy as np
from Code.locate_marker import MarkerDetector
from coppeliasim_zmqremoteapi_client import RemoteAPIClient
from Code.rrt_star_visualise import visualise_point

"""
Testowanie detekcji i lokalizaji markerów aruco
"""

def main():
    client = RemoteAPIClient()
    sim = client.require('sim')
    print("[Main] Starting simulation...")
    sim.setStepping(True) # (by defalt step is 0.05 seconds)
    sim.startSimulation() 
    visualise_image = False

    # image needs to be from vision sensor (camera image is not processable by api)
    vision_sensor_handle = sim.getObject('/visionSensor')
    rover_handle = sim.getObject('/Chassis')
    markerdetector = MarkerDetector(sim, vision_sensor_handle, rover_handle)
    sim.step()
    #matrix = markerdetector.get_camera_location()
    # get image
    img, [resX, resY] = sim.getVisionSensorImg(vision_sensor_handle)
    img = np.frombuffer(img, dtype=np.uint8).reshape(resY, resX, 3)
    img = cv2.flip(cv2.cvtColor(img, cv2.COLOR_BGR2RGB), 0)
    # find markers
    new_img, markers = markerdetector.locate_marker(img, visualise_image)
    # there are markers then locate then
    if markers:
        for marker in markers:
            tvec = marker[2]
            rotm = marker[3]
            marker_position, marker_orientation = markerdetector.calculate_marker_location(tvec, rotm)
            print(f"Found marker! \n at:{marker_position[0]},{marker_position[1]},{marker_position[2]}  \n with orientation:{marker_orientation[0]},{marker_orientation[1]},{marker_orientation[2]}")
    # no i w sumie bierzemy tylko x i y z tego
    sh = visualise_point(sim, [marker_position[0], marker_position[1]], 1)

    try:
        while True:

            sim.step()

    except KeyboardInterrupt:
        print("[Main] Stopping...")
        sim.stopSimulation()
        print("[Main] Simulation stopped.")


if __name__ == "__main__":
    main()
