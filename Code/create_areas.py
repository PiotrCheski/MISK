import random
import os
import json
import cv2
from coppeliasim_zmqremoteapi_client import RemoteAPIClient

from new_aruco import generate_aruco_textures
from area import Area

client = RemoteAPIClient()
sim = client.require('sim')

# ToDo: dodać teksturę do pól
# ToDo: dodać markery na środku każdego pola

# Ścieżka do katalogu bieżącego skryptu
current_dir = os.path.dirname(os.path.abspath(__file__))

# Ścieżka do tekstury (plik dirt.jpg znajduje się w folderze nadrzędnym względem folderu, w którym jest skrypt)
texture_path = os.path.join(current_dir, "..", "Textures", "dirt.jpg")
textures_dir = os.path.join(current_dir, "..", "Textures")

sizes = [1.0, 1.0, 0.1]
options = 0
num_planes = 1
occupied_positions = []
plane_size = sizes[0] * sizes[1]
microbiome_types = ["Bacteria", "Fungi", "Algae", "Archaea"]
areas = []

# Load texture
texture_path = os.path.join(current_dir, "..", "Textures", "dirt_with_aruco.jpg")
texture_handle, texture_id, res = sim.createTexture(texture_path, 0)

## Save the new texture with the marker overlayed
#def save_new_texture_with_marker(texture, output_path="Textures/texture_with_marker.jpg"):
#    cv2.imwrite(output_path, texture)
#    return output_path

def is_overlapping(x, y):
    for px, py in occupied_positions:
        if abs(px - x) < plane_size and abs(py - y) < plane_size:
            return True
    return False

def generate_areas():
    grid_rows = 5
    grid_cols = 5
    amount_of_areas = grid_rows * grid_cols - 1 # na środku jest centrala
    generate_aruco_textures(texture_path, textures_dir, amount_of_areas)
    spacing = 2.0
    start_x = -((grid_cols - 1) * spacing) / 2
    start_y = -((grid_rows - 1) * spacing) / 2
    index = 0

    middle_col = grid_cols // 2
    middle_row = grid_rows // 2

    for row in range(grid_rows):
        for col in range(grid_cols):
            if row == middle_row and col == middle_col:
                continue
            x = start_x + col * spacing
            y = start_y + row * spacing
            z = 0.25

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
            texture_path_local = os.path.join(current_dir, "..", "Textures", f"dirt_with_aruco_{index}.jpg")
            print(texture_path_local)
            texture_handle, texture_id, res = sim.createTexture(texture_path_local, 0)
            sim.setShapeTexture(plane_handle, texture_id, sim.texturemap_plane, 1, [1.5,1.5])

            soil_data = {
                "area": (area.x, area.y, area.z),
                "humidity": humidity,
                "pH": pH,
                "microbiome": microbiome,
                "temperature": temperature,
                "minerals": mineral_composition
            }
            sim.writeCustomDataBlock(plane_handle, "SoilData", json.dumps(soil_data).encode('utf-8'))

            index += 1

    for area in areas:
        print(area)

    print(f"Created {len(areas)} grid-based planes with parameters.")
    return areas


#def generate_areas():
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
