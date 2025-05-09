import cv2
import numpy as np
from scipy.spatial.transform import Rotation as R

# WIP
# wykrywanie i lokalizowanie markeru na podstawie obrazu z kamery
# muszę jeszcze ogarnąć: transformatę: kamera->łazik->mapa (zwracanie lokalizacji)

# transformata: t_camera_rover -> jak będzie konstrukcja łązika to wtedy z budowy samej

# transformata: t_rover_map
"""
local m = sim.getObjectMatrix(handle, -1)
T = np.array([
    [m[0], m[4], m[8], m[3]],
    [m[1], m[5], m[9], m[7]],
    [m[2], m[6], m[10], m[11]],
    [0,    0,    0,    1]
])
"""


def get_camera_parameters(sim, vision_sensor_handle):
    # Pobierz rozdzielczość sensora (szerokość, wysokość)
    resolution = sim.getVisionSensorResolution(vision_sensor_handle)
    width, height = resolution[0], resolution[1]
    # Pobierz pionowe pole widzenia (w radianach)
    fov_y = sim.getVisionSensorFov(vision_sensor_handle)

    # Zakładamy square pixels, więc fx = fy
    fy = height / (2 * np.tan(fov_y / 2))
    fx = fy
    # Główna oś obrazu (zwykle środek)
    cx = width / 2
    cy = height / 2
    # Macierz kamery OpenCV
    camera_matrix = np.array([
        [fx,  0, cx],
        [ 0, fy, cy],
        [ 0,  0,  1]
    ], dtype=np.float32)
    # Brak dystorsji optycznej
    distortion_coeffs = np.zeros((4, 1), dtype=np.float32)

    return camera_matrix, distortion_coeffs

def locate_marker(img, show=False):
    markers = []
    # Camera parameters -> to z funkcji wyżej, na razie placeholder
    camera_matrix = np.array([[1000, 0, 320], [0, 1000, 240], [0, 0, 1]], dtype=np.float32)
    # kamera w copelli jest idealna -> zerosy
    distortion_coeffs = np.zeros((4, 1))
    # ArUco params
    aruco_dict = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
    aruco_params = cv2.aruco.DetectorParameters()
    # Marker size and corner points
    marker_length = 0.05 
    half_length = marker_length / 2
    corner_points = np.array([
            [-half_length,  half_length, 0],
            [ half_length,  half_length, 0],
            [ half_length, -half_length, 0],
            [-half_length, -half_length, 0]
        ], dtype=np.float32)
    detector = cv2.aruco.ArucoDetector(aruco_dict, aruco_params)
    # Convert to OpenCV format -> chyba już jest z exampla    
    # Convert image to greyscale
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    # Create detector
    corners, ids, rejects = detector.detectMarkers(gray)
    # If there is detection
    if ids is not None:
        # Draw detected markers
        cv2.aruco.drawDetectedMarkers(img, corners, ids)
        # Go through deceted markers
        for i in range(len(ids)):
            # Calcualte marker position
            img_points = corners[i].reshape(-1, 2)
            success, rvec, tvec = cv2.solvePnP(corner_points, img_points, camera_matrix, distortion_coeffs)
            if success:
                # Locate them on image and return position
                cv2.drawFrameAxes(img, camera_matrix, distortion_coeffs, rvec, tvec, 0.1)
                #rvec i tvec to macierz 3x1 a nie wektor więc musi być drugi indeks
                rotm, _ = cv2.Rodrigues(rvec)
                marker_data = {"id": ids[i][0],"rotation_vector ": rvec, "translation_vector ": tvec, "rotation_matrix": rotm}
                markers.append(marker_data)
                print(f"ID: {ids[i][0]}, Pozycja: X={tvec[0][0]:.2f}m, Y={tvec[1][0]:.2f}m, Z={tvec[2][0]:.2f}m")
    # return image with markers
    if show == True:
        cv2.imshow('', img)
        cv2.waitKey(1) # waits for click
    return img, markers


def calculate_marker_location(tvec, rotm, t_camera_rover, t_rover_map):
    # construct translation
    t_marker_camera = np.eye(4)
    t_marker_camera[:3, :3] = rotm
    t_marker_camera[:3, 3] = tvec.flatten()

    # calculate translation of marker im map frame
    t_maker_map = t_rover_map * t_camera_rover * t_marker_camera

    # convert to position and orientation
    marker_position = t_maker_map[:3, 3]
    marker_rotation = t_maker_map[:3, :3]
    rot = R.from_matrix(marker_rotation)
    marker_orientation = rot.as_euler('xyz', degrees=True)
    
    return marker_position, marker_orientation



    