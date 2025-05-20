def duplicate_rover(sim, source_name: str, new_name: str, position_offset):
    handle = sim.getObject(source_name)
    clone_handle = sim.copyPasteObjects([handle], 1)
    clone_handle = clone_handle[0]
    print(clone_handle)
    sim.setObjectAlias(clone_handle, new_name, True)
    sim.setObjectPosition(clone_handle, -1, [0, position_offset, 0.375])