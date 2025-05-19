import math
import time
import numpy as np

from coppeliasim_zmqremoteapi_client import RemoteAPIClient


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

def rotate_y(sim, joint_handle, angle, rotation_matrix_getter=get_rotation_matrix_y):
    ANGLE_CHANGE_PER_STEP = 20
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
        sim.step()
        #time.sleep(STEP_DURATION_SECS)

def grip(sim, rover_name, percent_open=1.0):
    FULL_OPEN_Y = 0.027
    CHANGE_PER_STEP = 0.01
    STEP_DURATION = 0.1
    handle = lambda joint_name: sim.getObject(
        f"/{rover_name}/{joint_name}"
    )
    endpoint_handle = handle('ArmEndpoint')
    endpoint_left_handle = handle('ArmEndpointLeft')
    endpoint_right_handle = handle('ArmEndpointRight')

    left_pos = sim.getObjectPosition(endpoint_left_handle, endpoint_handle)
    right_pos = sim.getObjectPosition(endpoint_right_handle, endpoint_handle)

    requested_y_pos = percent_open*FULL_OPEN_Y;
    left_y_pos_diff = -requested_y_pos - left_pos[1]
    right_y_pos_diff = requested_y_pos - right_pos[1]

    get_operator = lambda val: 1 if val >= 0 else -1
    steps = int(max(abs(right_y_pos_diff/CHANGE_PER_STEP), abs(left_y_pos_diff/CHANGE_PER_STEP)))
    for _ in range(1, steps+1):
        left_pos[1] = left_pos[1] + get_operator(left_y_pos_diff)*CHANGE_PER_STEP
        right_pos[1] = right_pos[1] + get_operator(right_y_pos_diff)*CHANGE_PER_STEP
        sim.setObjectPosition(endpoint_left_handle, endpoint_handle, left_pos)
        sim.setObjectPosition(endpoint_right_handle, endpoint_handle, right_pos)
        sim.step()
        #time.sleep(STEP_DURATION)

def deploy_arm(sim, rover_name):
    joint_handle = lambda joint_name: sim.getObject(
        f"/{rover_name}/{joint_name}"
    )
    rotate_y(sim, joint_handle('ArmJoint1'), 90)
    rotate_y(sim, joint_handle('ArmJoint2'), 90)

def retract_arm(sim, rover_name):
    joint_handle = lambda joint_name: sim.getObject(
        f"/{rover_name}/{joint_name}"
    )
    rotate_y(sim, joint_handle('ArmJoint1'), -90)
    rotate_y(sim, joint_handle('ArmJoint2'), -90)

if __name__ == "__main__":
    client = RemoteAPIClient()
    sim = client.require("sim")
    sim.startSimulation()
    rover_name = "Rover"
    deploy_arm(sim, rover_name)
    grip(sim, rover_name, 0.5)
    sim.step()
    retract_arm(sim, rover_name)
    grip(sim, rover_name, 1.0)
