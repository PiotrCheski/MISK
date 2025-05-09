from coppeliasim_zmqremoteapi_client import RemoteAPIClient

def remove_objects_with_prefix(prefix="Plane"):
    client = RemoteAPIClient()
    sim = client.require('sim')

    sim.setStepping(True)  # tryb krokowy jeśli symulacja działa
    sim.startSimulation()

    all_objects = sim.getObjectsInTree(sim.handle_scene)
    removed_count = 0

    for obj_handle in all_objects:
        name = sim.getObjectAlias(obj_handle)
        if name.startswith(prefix):
            sim.removeObject(obj_handle)
            print(f"Removed: {name}")
            removed_count += 1

    print(f"Done. Removed {removed_count} objects.")

if __name__ == "__main__":
    remove_objects_with_prefix()
