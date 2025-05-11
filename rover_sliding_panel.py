# Kod do przetestowania poprawności zainstalowania biblioteki. Należy włączyć CoppeliaSim. Uruchomienie skryptu powinno uruchomić symulację w CoppeliaSim.
from coppeliasim_zmqremoteapi_client import RemoteAPIClient
import time

client = RemoteAPIClient()
sim = client.require('sim')

import time
from coppeliasim_zmqremoteapi_client import RemoteAPIClient

def deploy_solar_panels(rover_name: str, extension: float = 0.25, duration: float = 2.0):
    """
    Wysuwa jednocześnie lewy i prawy panel słoneczny z łazika w CoppeliaSim.

    :param rover_name: nazwa łazika w scenie, np. 'Chassis'
    :param extension: dystans wysuwania w metrach (domyślnie 0.25)
    :param duration: czas animacji w sekundach (domyślnie 2.0)
    """
    client = RemoteAPIClient()
    sim = client.getObject('sim')

    # Uchwyt do łazika
    rover_handle = sim.getObject(f'/{rover_name}')

    # Nazwy paneli
    left_panel_path = f"/{rover_name}/SolarPanel_Left"
    right_panel_path = f"/{rover_name}/SolarPanel_Right"

    left_panel_handle = sim.getObject(left_panel_path)
    right_panel_handle = sim.getObject(right_panel_path)

    # Pozycje startowe i końcowe
    start_pos_left = sim.getObjectPosition(left_panel_handle, rover_handle)
    start_pos_right = sim.getObjectPosition(right_panel_handle, rover_handle)

    end_pos_left = start_pos_left.copy()
    end_pos_right = start_pos_right.copy()

    # Lewy panel w -Y, prawy w +Y (możesz zmienić na X, jeśli masz inną oś wysuwu)
    end_pos_left[1] -= extension
    end_pos_right[1] += extension

    steps = int(duration / 0.01)

    for i in range(steps + 1):
        t = i / steps

        interp_left = [
            start_pos_left[0] + t * (end_pos_left[0] - start_pos_left[0]),
            start_pos_left[1] + t * (end_pos_left[1] - start_pos_left[1]),
            start_pos_left[2] + t * (end_pos_left[2] - start_pos_left[2])
        ]
        interp_right = [
            start_pos_right[0] + t * (end_pos_right[0] - start_pos_right[0]),
            start_pos_right[1] + t * (end_pos_right[1] - start_pos_right[1]),
            start_pos_right[2] + t * (end_pos_right[2] - start_pos_right[2])
        ]

        sim.setObjectPosition(left_panel_handle, rover_handle, interp_left)
        sim.setObjectPosition(right_panel_handle, rover_handle, interp_right)

        time.sleep(0.01)


sim.startSimulation()
deploy_solar_panels('Chassis')  # wysuwa oba panele jednocześnie