def duplicate_rover(sim, source_name: str, new_name: str, pos_x, pos_y, pos_z=0.375):
    handle = sim.getObject(source_name)
    clone_handle = sim.copyPasteObjects([handle], 1)
    clone_handle = clone_handle[0]
    print(clone_handle)
    sim.setObjectAlias(clone_handle, new_name, True)
    sim.setObjectPosition(clone_handle, -1, [pos_x, pos_y, pos_z])