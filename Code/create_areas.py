import random
import os
import json
import cv2
from coppeliasim_zmqremoteapi_client import RemoteAPIClient
from Code.area import Area

client = RemoteAPIClient()
sim = client.require('sim')

# ToDo: dodać teksturę do pól
# ToDo: dodać markery na środku każdego pola

sizes = [1.0, 1.0, 0.1]
options = 0
num_planes = 20
occupied_positions = []
plane_size = sizes[0] * sizes[1]
microbiome_types = ["Bacteria", "Fungi", "Algae", "Archaea"]
areas = []

# Load texture
current_dir = os.path.dirname(os.path.abspath(__file__))
texture_path = os.path.join(current_dir, "..", "Textures", "dirt_with_aruco.jpg")
texture_handle, texture_id, res = sim.createTexture(texture_path, 0)

# Save the new texture with the marker overlayed
def save_new_texture_with_marker(texture, output_path="Textures/texture_with_marker.jpg"):
    cv2.imwrite(output_path, texture)
    return output_path

def is_overlapping(x, y):
    for px, py in occupied_positions:
        if abs(px - x) < plane_size and abs(py - y) < plane_size:
            return True
    return False

def generate_areas():
    for index in range(num_planes):
        while True:
            x = round(random.uniform(-6.5, 6.5), 2)
            y = round(random.uniform(-6.5, 6.5), 2)
            z = 0.25

            if not is_overlapping(x, y):
                occupied_positions.append((x, y))
                break

        # Generate soil parameters
        humidity = round(random.uniform(40.0, 70.0), 2)
        pH = round(random.uniform(5.5, 8.0), 2)
        microbiome = random.choice(microbiome_types)
        temperature = round(random.uniform(15.0, 30.0), 2)
        mineral_composition = "Silicon, Iron"

        area = Area(x, y, z, humidity, pH, microbiome, temperature, mineral_composition)
        areas.append(area)


        plane_handle = sim.createPrimitiveShape(sim.primitiveshape_plane, sizes, options)
        sim.setObjectPosition(plane_handle, sim.handle_world, [x, y, z])
        sim.setObjectName(plane_handle, f"Field_{index}")
        
        sim.setShapeTexture(plane_handle, texture_id, sim.texturemap_plane, 1, [1.5,1.5])

        # Write soil data as custom data block
        soil_data = {
            "area": (area.x, area.y, area.z),
            "humidity": humidity,
            "pH": pH,
            "microbiome": microbiome,
            "temperature": temperature,
            "minerals": mineral_composition
        }
        sim.writeCustomDataBlock(plane_handle, "SoilData", json.dumps(soil_data).encode('utf-8'))

    # Print summary
    for area in areas:
        print(area)

    print(f"Created {num_planes} non-overlapping planes with parameters.")
    return areas
