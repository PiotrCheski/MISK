import random
from coppeliasim_zmqremoteapi_client import RemoteAPIClient


client = RemoteAPIClient()
sim = client.require('sim')

# Create a plane
primitive_type = 0  # 0 represents a plane
sizes = [1.0, 1.0, 0.1]  
options = 0  

num_planes = 10
occupied_positions = [] 
plane_size = sizes[0]*sizes[1]  

def is_overlapping(x, y):
    for px, py in occupied_positions:
        if abs(px - x) < plane_size and abs(py - y) < plane_size:
            return True  # Planes overlap
    return False

for _ in range(num_planes):
    while True:
        x = round(random.uniform(-4.5, 4.5), 2)  
        y = round(random.uniform(-4.5, 4.5), 2)
        z = 0.20  
        
        if not is_overlapping(x, y):
            occupied_positions.append((x, y))
            break
    
    # Create the shape in CoppeliaSim
    plane_handle = sim.createPrimitiveShape(sim.primitiveshape_plane, sizes, options)
    sim.setObjectColor(plane_handle, 0, 0, [0.0, 1.0, 0.0])  # Green color
    sim.setObjectPosition(plane_handle, sim.handle_world, [x, y, z])

print("Created 20 non-overlapping planes at:", occupied_positions)