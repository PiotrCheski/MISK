import random
from coppeliasim_zmqremoteapi_client import RemoteAPIClient

client = RemoteAPIClient()
sim = client.require('sim')
                     
# ToDo: dodać teksturę do pól
# ToDo: dodać markery na środku każdego pola

class Area:
    def __init__(self, x, y, z, humidity, pH, microbiome, temperature, mineral_composition):
        self.x = x
        self.y = y
        self.z = z
        self.humidity = humidity
        self.pH = pH
        self.microbiome = microbiome
        self.temperature = temperature
        self.mineral_composition = mineral_composition

    def __str__(self):
        return (f"Area ({self.x}, {self.y}, {self.z})\n"
                f"Humidity: {self.humidity}%\n"
                f"pH: {self.pH}\n"
                f"Microbiome: {self.microbiome}\n"
                f"Temperature: {self.temperature}°C\n"
                f"Mineral Composition: {self.mineral_composition}")

sizes = [1.0, 1.0, 0.1]  
options = 0  

num_planes = 4
occupied_positions = [] 
plane_size = sizes[0]*sizes[1]  

def is_overlapping(x, y):
    for px, py in occupied_positions:
        if abs(px - x) < plane_size and abs(py - y) < plane_size:
            return True 
    return False

microbiome_types = ["Bacteria", "Fungi", "Algae", "Archaea"]
areas = []

for _ in range(num_planes):
    while True:
        x = round(random.uniform(-6.5, 6.5), 2)  
        y = round(random.uniform(-6.5, 6.5), 2)
        z = 0.20  # Height of the plane
        
        if not is_overlapping(x, y):
            occupied_positions.append((x, y))
            break
    
    # Generate random environmental parameters
    humidity = round(random.uniform(40.0, 70.0), 2)
    pH = round(random.uniform(5.5, 8.0), 2)
    microbiome = random.choice(microbiome_types)
    temperature = round(random.uniform(15.0, 30.0), 2)
    mineral_composition = "Silicon, Iron" 
    
    area = Area(x, y, z, humidity, pH, microbiome, temperature, mineral_composition)
    areas.append(area)
    
    plane_handle = sim.createPrimitiveShape(sim.primitiveshape_plane, sizes, options)
    sim.setObjectColor(plane_handle, 0, 0, [0.0, 1.0, 0.0])  # Green color
    sim.setObjectPosition(plane_handle, sim.handle_world, [x, y, z])

for area in areas:
    print(area)

print(f"Created {num_planes} non-overlapping planes at:")