from enum import Enum
import logging
import threading


def singleton(cls):
    instances = {}

    def get_instance(*args, **kwargs):
        if cls not in instances:
            instances[cls] = cls(*args, **kwargs)
        return instances[cls]

    return get_instance


class PanelState(Enum):
    HIDDEN = 0
    EXTENDED = 1


class WeatherState(Enum):
    SUNNY = 0
    DARK = 1


class ActivityState(Enum):
    IDLE = "idle"
    MOVING = "moving"
    WORKING = "working"
    CHARGING = "charging"


class Battery:
    MIN_CAPACITY = 0
    MAX_CAPACITY = 100
    # rates per tick
    BATTERY_CHANGE_RATES = {
        ActivityState.IDLE: -1,
        ActivityState.MOVING: -10,
        ActivityState.WORKING: -5,
        ActivityState.CHARGING: 10,
    }

    def __init__(self):
        self._charge = 100

    def _clamp_charge(self):
        self._charge = max(Battery.MIN_CAPACITY, min(self._charge, Battery.MAX_CAPACITY))

    def is_empty(self):
        return self._charge == Battery.MIN_CAPACITY

    def is_full(self):
        return self._charge == Battery.MAX_CAPACITY

    def tick(self, activity_state: ActivityState, has_charging_conditions: bool):
        prev_charge = self._charge
        if activity_state == ActivityState.CHARGING and not has_charging_conditions:
            pass
        else:
            self._charge += Battery.BATTERY_CHANGE_RATES[activity_state]

        self._clamp_charge()
        logging.info(
            f"Battery tick -- state: {activity_state.value}, can_charge: {has_charging_conditions} | {prev_charge} -> {self._charge}"
        )


@singleton
class RoverState:
    UPDATE_INTERVAL_SECS = 1

    def __init__(self):
        # Default states
        self._panel_state = PanelState.HIDDEN
        self._weather_state = WeatherState.SUNNY
        self._activity_state = ActivityState.IDLE
        # Battery
        self._battery = Battery()
        # Update periodically
        self._update_thread = threading.Thread(target=self.__update_cb)
        self._update_thread_stop_event = threading.Event()
        self._update_thread.start()

    def battery(self):
        return self._battery

    def has_charging_conditions(self):
        return self._weather_state == WeatherState.SUNNY and self._panel_state == PanelState.EXTENDED

    def is_charging(self):
        return self._activity_state == ActivityState.CHARGING;

    def set_panel_state(self, panel_state: PanelState):
        self._panel_state = panel_state
        return self

    def set_weather_state(self, weather_state: WeatherState):
        self._weather_state = weather_state
        return self

    def set_activity_state(self, activity_state: ActivityState):
        if self._activity_state == ActivityState.CHARGING:
            logging.warning(
                f"Cannot change activity when rover is in '{ActivityState.CHARGING}' state."
            )
            return self

        self._activity_state = activity_state
        return self

    def __maybe_update_state(self):
        if self._battery.is_empty() and self._activity_state != ActivityState.CHARGING:
            logging.info(
                f"Battery has run out; setting state to '{ActivityState.CHARGING}'."
            )
            self._activity_state = ActivityState.CHARGING
            return self

        if self._battery.is_full() and self._activity_state == ActivityState.CHARGING:
            logging.info(
                f"Battery recharged; removing the '{ActivityState.CHARGING}' state."
            )
            self._activity_state = ActivityState.IDLE
            return self

    def __update_cb(self):
        while not self._update_thread_stop_event.is_set():
            self.__update()
            self._update_thread_stop_event.wait(self.UPDATE_INTERVAL_SECS)

    def __update(self):
        self.__maybe_update_state()
        self._battery.tick(self._activity_state, self.has_charging_conditions())


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="[%(asctime)s] [%(filename)s] %(message)s",
        datefmt="%H:%M:%S",
    )

    rover_state = RoverState().set_activity_state(ActivityState.MOVING).set_panel_state(PanelState.EXTENDED)
