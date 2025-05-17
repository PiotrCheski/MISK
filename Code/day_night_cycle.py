import logging
import math
import threading

from coppeliasim_zmqremoteapi_client import RemoteAPIClient

client = RemoteAPIClient()
sim = client.require("sim")

def singleton(cls):
    instances = {}

    def get_instance(*args, **kwargs):
        if cls not in instances:
            instances[cls] = cls(*args, **kwargs)
        return instances[cls]

    return get_instance


@singleton
class DayNightCycle:
    DAY_DURATION_SECS = 60
    UPDATE_PERIOD_SECS = 1
    LINEAR_ATTENUATION_LOW = 0.0001  # Bright
    LINEAR_ATTENUATION_HIGH = 10 # Dark
    LIGHT_LABEL = "/DefaultLights/Sun"

    def __init__(self):
        client = RemoteAPIClient()
        self._sim = client.require("sim")
        self._light_handle = sim.getObject(self.LIGHT_LABEL)

        self._moment = 0
        self._brightness = None
        self._linear_attenuation = None

        self._update_thread = threading.Thread(target=self.__update_cb)
        self._update_thread_stop_event = threading.Event()
        self._update_thread.start()

    def is_day(self):
        return self._brightness >= 0.4

    def is_night(self):
        return not self.is_day()

    def __get_attenuation_list(self, linear_attenuation):
        return [0.001, linear_attenuation, 0.0001]

    def __update_cb(self):
        while not self._update_thread_stop_event.is_set():
            self.__update()
            self._update_thread_stop_event.wait(self.UPDATE_PERIOD_SECS)

    def __update(self):
        # prev_moment = self._moment
        # prev_brightness = self._brightness
        # prev_linear_attenuation = self._linear_attenuation

        self._moment = (self._moment + self.UPDATE_PERIOD_SECS) % self.DAY_DURATION_SECS

        day_fraction = self._moment / self.DAY_DURATION_SECS
        self._brightness = (math.cos(day_fraction * 2 * math.pi - math.pi) + 1) / 2
        self._linear_attenuation = (
            self.LINEAR_ATTENUATION_HIGH
            * (self.LINEAR_ATTENUATION_LOW / self.LINEAR_ATTENUATION_HIGH) ** self._brightness
        )
        sim.setFloatArrayProperty(
            self._light_handle,
            "attenuationFactors",
            self.__get_attenuation_list(self._linear_attenuation),
        )

        # if prev_linear_attenuation is not None:
        #     logging.info(
        #         f"Moment: {prev_moment:.1f}->{self._moment:.1f} | "
        #         f"Brightness: {prev_brightness:.3f}->{self._brightness:.3f} | "
        #         f"Attenuation: {prev_linear_attenuation:.6f}->{self._linear_attenuation:.6f} | "
        #         f"State: {"day" if self.is_day() else "night"}"
        #     )


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="[%(asctime)s] [%(filename)s] %(message)s",
        datefmt="%H:%M:%S",
    )

    # Start simulation
    sim.startSimulation()
    DayNightCycle()
