# It creates only object

from coppeliasim_zmqremoteapi_client import RemoteAPIClient

# utils.py

def create_centrala_cube(sim):
    size = [0.5, 0.5, 0.5]
    position = [0, 0, size[2] / 2]
    options = 0
    handle = sim.createPrimitiveShape(sim.primitiveshape_cuboid, size, options)
    sim.setObjectPosition(handle, -1, position)
    sim.setObjectInt32Param(handle, sim.shapeintparam_static, 1)
    sim.setObjectName(handle, "CentralaCube")
    
