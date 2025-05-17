import math
import time
import numpy as np

from coppeliasim_zmqremoteapi_client import RemoteAPIClient

client = RemoteAPIClient()
sim = client.require("sim")


def get_rotation_matrix_x(theta_deg):
    theta = math.radians(theta_deg)
    c = math.cos(theta)
    s = math.sin(theta)
    return [1, 0, 0, 0, 0, c, -s, 0, 0, s, c, 0, 0, 0, 0, 1]


def get_rotation_matrix_y(theta_deg):
    theta = math.radians(theta_deg)
    c = math.cos(theta)
    s = math.sin(theta)
    return [c, 0, s, 0, 0, 1, 0, 0, -s, 0, c, 0, 0, 0, 0, 1]


def get_rotation_matrix_z(theta_deg):
    theta = math.radians(theta_deg)
    c = math.cos(theta)
    s = math.sin(theta)
    return [c, -s, 0, 0, s, c, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1]

def to_numpy_array(lst):
    return np.array(lst).reshape(4, 4)

def to_list(np_array):
    return np_array.flatten().tolist()

def rotate_y(joint_handle, angle, rotation_matrix_getter=get_rotation_matrix_y):
    ANGLE_CHANGE_PER_STEP = 5
    STEP_DURATION_SECS = 0.1
    direction = 1 if angle >= 0 else -1
    steps = abs(angle) // ANGLE_CHANGE_PER_STEP

    for _ in range(steps):
        current_rotation_mat = sim.getJointMatrix(joint_handle) + [0, 0, 0, 1]
        rotation_matrix_delta = rotation_matrix_getter(direction * ANGLE_CHANGE_PER_STEP)

        rotation_matrix = to_list(
            np.dot(to_numpy_array(rotation_matrix_delta), to_numpy_array(current_rotation_mat))
        )

        sim.setSphericalJointMatrix(joint_handle, rotation_matrix)
        time.sleep(STEP_DURATION_SECS)

def deploy_arm(rover_name):
    joint_handle = lambda joint_name: sim.getObject(
        f"/{rover_name}/{joint_name}"
    )
    rotate_y(joint_handle('ArmJoint1'), 90)
    rotate_y(joint_handle('ArmJoint2'), 90)

def retract_arm(rover_name):
    joint_handle = lambda joint_name: sim.getObject(
        f"/{rover_name}/{joint_name}"
    )
    rotate_y(joint_handle('ArmJoint1'), -90)
    rotate_y(joint_handle('ArmJoint2'), -90)

if __name__ == "__main__":
    rover_name = "Chassis"
    deploy_arm(rover_name)
    time.sleep(1)
    retract_arm(rover_name)
