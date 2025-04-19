import cv2
import numpy as np

# WIP
# wykrywanie i lokalizowanie markeru na podstawie obrazu z kamery
# muszę jeszcze ogarnąć: parametry kamery, transformatę: kamera->łazik->mapa, zwracanie lokalizacji

def locate_marker(img, show=False):
    # Camera parameters -> NEED CALIBRATION FROM SIM !
    camera_matrix = np.array([[1000, 0, 320], [0, 1000, 240], [0, 0, 1]], dtype=np.float32)
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
                print(f"ID: {ids[i][0]}, Pozycja: X={tvec[0][0]:.2f}m, Y={tvec[1][0]:.2f}m, Z={tvec[2][0]:.2f}m")
    # return image with markers
    return img
    