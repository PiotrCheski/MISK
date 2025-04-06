import yaml
import os

config_path = os.path.join(os.path.dirname(__file__), "rrt_star_config.yaml")
with open(config_path, 'r') as file:
    config = yaml.safe_load(file)
sizes = config['sizes']
height = config['height']

def visualise_point(sim, point, index, color=[0,0,1]):
    # visualize points as spheres
    options = 0
    point_handle = sim.createPrimitiveShape(sim.primitiveshape_spheroid, sizes, options)
    sim.setObjectPosition(point_handle, sim.handle_world, [point[0], point[1], height])
    sim.setShapeColor(point_handle, None, sim.colorcomponent_ambient_diffuse, color)
    sim.setObjectAlias(point_handle, f"Planner_point_{index}")
    # wyłączanie kolizji i fizyki dla obiektu
    sim.setObjectInt32Param(point_handle, sim.shapeintparam_respondable, 0) 
    sim.setObjectInt32Param(point_handle, sim.shapeintparam_static, 1) 
    return point_handle

def visualise_obstacles(sim, points, index, color=[1,0,0]):
    # visualize points as spheres
    options = 0
    obstacle_handles = []
    for point in points:
        obstacle_size = [sizes[0] + point[2], sizes[1] + point[2] ,sizes[2]]
        point_handle = sim.createPrimitiveShape(sim.primitiveshape_spheroid, obstacle_size, options)
        sim.setObjectPosition(point_handle, sim.handle_world, [point[0], point[1], height])
        sim.setShapeColor(point_handle, None, sim.colorcomponent_ambient_diffuse, color)
        sim.setObjectAlias(point_handle, f"Planner_obstacle_{index}")
        # wyłączanie kolizji i fizyki dla obiektu
        sim.setObjectInt32Param(point_handle, sim.shapeintparam_respondable, 0) 
        sim.setObjectInt32Param(point_handle, sim.shapeintparam_static, 1) 
        obstacle_handles.append(point_handle)
        index+=1
    return obstacle_handles

def visualise_path(sim, path, index, color= [0.0,1.0,0.0]):
    options = 0
    points_handles = []
    # visualize points as spheres
    for id in range(len(path)):
        point = path[id]
        point_handle = sim.createPrimitiveShape(sim.primitiveshape_spheroid, sizes, options)
        sim.setObjectPosition(point_handle, sim.handle_world, [point[0], point[1], height])
        sim.setShapeColor(point_handle, None, sim.colorcomponent_ambient_diffuse, color)
        sim.setObjectAlias(point_handle, f"Planner_path_{index}_point_{id}")  
        # wyłączanie kolizji i fizyki dla obiektu
        sim.setObjectInt32Param(point_handle, sim.shapeintparam_respondable, 0) 
        sim.setObjectInt32Param(point_handle, sim.shapeintparam_static, 1) 
        points_handles.append(point_handle) 
    # connect spheres
    thickness=2.0
    line_handle = sim.addDrawingObject(sim.drawing_lines, thickness, 0.0, -1, 2*len(path), color)
    for i in range(len(path)-1):
        start_point = [path[i][0], path[i][1], height]
        end_point = [path[i+1][0], path[i+1][1], height]
        sim.addDrawingObjectItem(line_handle, start_point + end_point)
    return points_handles, line_handle

def remove_point(sim, handle):
    if sim.isHandle(handle):
        sim.removeObject(handle)

def remove_path(sim, points_handles, line_handle):
    for handle in points_handles:
        if sim.isHandle(handle):
            sim.removeObject(handle)
    if sim.isHandle(line_handle):
            sim.removeDrawingObject(line_handle)