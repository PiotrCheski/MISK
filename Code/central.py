import json
import time
import threading
from coppeliasim_zmqremoteapi_client import RemoteAPIClient
from area import Area

class Centrala:
    def __init__(self):
        self.client = RemoteAPIClient()
        self.sim = self.client.require('sim')
        self.fields = []
        self.running = True
        self.centrala_handle = None
        self._create_centrala_cube()
        self._load_fields_from_scene()

    def _create_centrala_cube(self):
        size = [0.5, 0.5, 0.5]
        position = [0, 0, size[2] / 2]
        options = 0
        self.centrala_handle = self.sim.createPrimitiveShape(
            self.sim.primitiveshape_cuboid, size, options
        )
        self.sim.setObjectPosition(self.centrala_handle, -1, position)
        self.sim.setObjectInt32Param(self.centrala_handle, self.sim.shapeintparam_static, 1)
        self.sim.setObjectName(self.centrala_handle, "CentralaCube")
        print("[Centrala] Cube created.")

    def _load_fields_from_scene(self):
        index = 0
        while True:
            name = f"Field_{index}"
            try:
                print(f"[Centrala] Looking for field {name}...")
                handle = self.sim.getObjectHandle(name)
                pos = self.sim.getObjectPosition(handle, -1)
                data_raw = self.sim.readCustomDataBlock(handle, "SoilData")

                if not data_raw:
                    raise ValueError(f"No SoilData found for {name}")

                data = json.loads(data_raw)

                # Validate all required keys
                required_keys = ["humidity", "pH", "microbiome", "temperature", "minerals"]
                for key in required_keys:
                    if key not in data:
                        raise KeyError(f"[Centrala] Missing '{key}' in SoilData for {name}")

                # Create Area object
                area = Area(
                    pos[0], pos[1], pos[2],
                    data["humidity"],
                    data["pH"],
                    data["microbiome"],
                    data["temperature"],
                    data["minerals"]
                )
                self.fields.append(area)
                print(f"[Centrala] Loaded {name}: {area}")
                index += 1
            except Exception as e:
                print(f"[Centrala] No more fields found")
                break

    def monitor_fields(self):
        for field in self.fields:
            if field.humidity < 50:
                print(f"[Centrala] Field at ({field.x}, {field.y}) needs watering!")
            if field.pH < 6.0:
                print(f"[Centrala] Field at ({field.x}, {field.y}) pH too low!")

    def periodic_check(self):
        while self.running:
            print("\n[Centrala] Checking fields...")
            self.monitor_fields()
            time.sleep(5)

    def stop(self):
        self.running = False

if __name__ == "__main__":
    centrala = Centrala()
    try:
        t = threading.Thread(target=centrala.periodic_check)
        t.start()
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        centrala.stop()
        print("\n[Centrala] Stopped.")
