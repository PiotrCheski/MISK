# Kod do przetestowania poprawności zainstalowania biblioteki. Należy włączyć CoppeliaSim. Uruchomienie skryptu powinno uruchomić symulację w CoppeliaSim.
from coppeliasim_zmqremoteapi_client import RemoteAPIClient

client = RemoteAPIClient()
sim = client.require('sim')
goal_handle = sim.getObject('/dummy')
end_pos = sim.getObjectPosition(goal_handle, -1)
print(end_pos)

#sim.startSimulation()
