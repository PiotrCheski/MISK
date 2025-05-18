# Goal of this file: Prepare simulation env:
# 1. Load scene
# 2. Generate areas
import os

from coppeliasim_zmqremoteapi_client import RemoteAPIClient

from create_areas import generate_areas
from create_centrala import create_centrala_cube


client = RemoteAPIClient()
sim = client.require('sim')

print("[Main] Loading Mars terrain scene...")
    
# current_dir = os.path.dirname(os.path.abspath(__file__))
# scene_path = os.path.join(current_dir, "mars_terrain.ttt")

#sim.loadScene(scene_path)
print("[Main] Scene loaded.")

print("[Main] Generating areas...")
generate_areas() 
print("[Main] Areas generated.")

print("[Main] Generating Centrala...")
#create_centrala_cube(sim)
print("[Centrala] Centrala created.")