# Kod do przetestowania poprawności zainstalowania biblioteki. Należy włączyć CoppeliaSim. Uruchomienie skryptu powinno uruchomić symulację w CoppeliaSim.
from coppeliasim_zmqremoteapi_client import RemoteAPIClient

client = RemoteAPIClient()
sim = client.require('sim')


#sim.startSimulation()
