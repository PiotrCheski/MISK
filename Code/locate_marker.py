import cv2
import numpy as np
from scipy.spatial.transform import Rotation as R
#from coppeliasim_zmqremoteapi_client import RemoteAPIClient

class MarkerDetector:
    def __init__(self, sim, vision_sensor_handle, rover_handle):
        # sim connection
        self.sim_ = sim
        # object handles
        self.vision_sensor_handle_ = vision_sensor_handle
        self.rover_handle_ = rover_handle
        # camera params
        self.camera_matrix_, self.distortion_coeffs_ = self.get_camera_parameters(self, self.vision_sensor_handle)
        # calclate constant transformation matrix rover->camera
        m = self.sim_.getObjectMatrix(self.rover_handle_, -1)
        t_rover_map = np.array([
        [m[0], m[4], m[8], m[3]],
        [m[1], m[5], m[9], m[7]],
        [m[2], m[6], m[10], m[11]],
        [0,    0,    0,    1]])
        m = self.sim_.getObjectMatrix(self.vision_sensor_handle_, -1)
        t_camera_map = np.array([
        [m[0], m[4], m[8], m[3]],
        [m[1], m[5], m[9], m[7]],
        [m[2], m[6], m[10], m[11]],
        [0,    0,    0,    1]])
        self.t_camera_rover_ = t_rover_map * t_camera_map^(-1)

    def get_camera_parameters(self, vision_sensor_handle):
        # Get sensor resolition
        resolution = self.sim_.getVisionSensorResolution(vision_sensor_handle)
        width, height = resolution[0], resolution[1]
        # Get sensor field of view (radians)
        fov_y = self.sim_.getVisionSensorFov(vision_sensor_handle)
        # Square pixels, so fx = fy
        fy = height / (2 * np.tan(fov_y / 2))
        fx = fy
        # Main axis of image (middle)
        cx = width / 2
        cy = height / 2
        # Camera matrix
        camera_matrix = np.array([
            [fx,  0, cx],
            [ 0, fy, cy],
            [ 0,  0,  1]
        ], dtype=np.float32)
        # No optical distortion
        distortion_coeffs = np.zeros((4, 1), dtype=np.float32)
        return camera_matrix, distortion_coeffs

    def locate_marker(self, img, show=False):
        markers = []
        # ArUco params -> CHANGE THIS IF NEEDED
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
                success, rvec, tvec = cv2.solvePnP(corner_points, img_points, self.camera_matrix_, self.distortion_coeffs_)
                if success:
                    # Locate them on image and return position
                    cv2.drawFrameAxes(img, self.camera_matrix_, self.distortion_coeffs_, rvec, tvec, 0.1)
                    # rvec and tvec is 3x1 matrix, not a vector so needs second index
                    rotm, _ = cv2.Rodrigues(rvec)
                    # marker_data = {"id": ids[i][0],"rotation_vector ": rvec, "translation_vector ": tvec, "rotation_matrix": rotm}
                    marker_data = [ids[i][0], rvec, tvec, rotm]
                    markers.append(marker_data)
                    print(f"ID: {ids[i][0]}, Pozycja: X={tvec[0][0]:.2f}m, Y={tvec[1][0]:.2f}m, Z={tvec[2][0]:.2f}m")
        # Return image with markers
        if show == True:
            cv2.imshow('', img)
            cv2.waitKey(1) # waits for click
        return img, markers


    def calculate_marker_location(self, tvec, rotm):
        # Construct translation
        t_marker_camera = np.eye(4)
        t_marker_camera[:3, :3] = rotm
        t_marker_camera[:3, 3] = tvec.flatten()

        # Create rover map transformation matrix
        m = self.sim_.getObjectMatrix(self.rover_handle_, -1)
        t_rover_map = np.array([
        [m[0], m[4], m[8], m[3]],
        [m[1], m[5], m[9], m[7]],
        [m[2], m[6], m[10], m[11]],
        [0,    0,    0,    1]])

        # Calculate translation of marker im map frame
        t_maker_map = t_rover_map * self.t_camera_rover_ * t_marker_camera

        # Convert to position and orientation
        marker_position = t_maker_map[:3, 3]
        marker_rotation = t_maker_map[:3, :3]
        rot = R.from_matrix(marker_rotation)
        marker_orientation = rot.as_euler('xyz', degrees=True)
        
        return marker_position, marker_orientation



    