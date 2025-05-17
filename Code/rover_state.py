from enum import Enum
import logging
import threading

from sliding_solar_panel import deploy_solar_panels, retract_solar_panels, sim
from day_night_cycle import DayNightCycle
from move_arm import deploy_arm, retract_arm


def multiton(cls):
    instances = {}

    def getinstance(id):
        if id not in instances:
            instances[id] = cls(id)
        return instances[id]

    return getinstance


class PanelState(Enum):
    HIDDEN = 0
    EXTENDED = 1


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
        self._charge = max(
            Battery.MIN_CAPACITY, min(self._charge, Battery.MAX_CAPACITY)
        )

    def is_empty(self):
        return self._charge == Battery.MIN_CAPACITY

    def is_full(self):
        return self._charge == Battery.MAX_CAPACITY

    def tick(self, id, activity_state: ActivityState, has_charging_conditions: bool):
        prev_charge = self._charge
        if activity_state == ActivityState.CHARGING and not has_charging_conditions:
            pass
        else:
            self._charge += Battery.BATTERY_CHANGE_RATES[activity_state]

        self._clamp_charge()
        logging.info(
            f"[{id}] Battery tick -- state: {activity_state.value}, can_charge: {has_charging_conditions} | {prev_charge} -> {self._charge}"
        )


@multiton
class RoverState:
    UPDATE_INTERVAL_SECS = 1

    def __init__(self, id):
        # The id should match the parameters passed to solar panel functions
        self._id = id
        # Default states
        self._panel_state = PanelState.HIDDEN
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
        return DayNightCycle().is_day() and self._panel_state == PanelState.EXTENDED

    def is_charging(self):
        return self._activity_state == ActivityState.CHARGING

    def set_activity_state(self, activity_state: ActivityState):
        id = self._id
        prev_state = self._activity_state
        state_changed_to = lambda state: prev_state != state and activity_state == state
        state_changed_from = lambda state: prev_state == state and activity_state != state

        if state_changed_to(ActivityState.CHARGING):
            deploy_solar_panels(id)
            self._panel_state = PanelState.EXTENDED
        elif state_changed_from(ActivityState.CHARGING):
            retract_solar_panels(id)
            self._panel_state = PanelState.HIDDEN

        if state_changed_to(ActivityState.WORKING):
            deploy_arm(id)
        elif state_changed_from(ActivityState.WORKING):
            retract_arm(id)

        self._activity_state = activity_state
        return self

    def __maybe_update_state(self):
        id = self._id
        if self._battery.is_empty() and self._activity_state != ActivityState.CHARGING:
            if not DayNightCycle().is_day():
                self.set_activity_state(ActivityState.IDLE)
                return self

            logging.info(
                f"[{id}] Battery has run out; setting state to '{ActivityState.CHARGING}' and deploying solar panels."
            )
            self.set_activity_state(ActivityState.CHARGING)
            return self

        if self._activity_state == ActivityState.CHARGING:
            if self._battery.is_full():
                logging.info(
                    f"[{id}] Battery recharged; removing the '{ActivityState.CHARGING}' state and retracting solar panels."
                )
            elif not DayNightCycle().is_day():
                logging.info(
                    f"[{id}] The sun is gone; removing the '{ActivityState.CHARGING}' state and retracting solar panels."
                )
            else:
                return self

            self.set_activity_state(ActivityState.IDLE)
            return self

        return self

    def __update_cb(self):
        while not self._update_thread_stop_event.is_set():
            self.__update()
            self._update_thread_stop_event.wait(self.UPDATE_INTERVAL_SECS)

    def __update(self):
        self.__maybe_update_state()
        self._battery.tick(
            self._id, self._activity_state, self.has_charging_conditions()
        )


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="[%(asctime)s] [%(filename)s] %(message)s",
        datefmt="%H:%M:%S",
    )

    sim.startSimulation()

    rover_state = RoverState("Chassis").set_activity_state(ActivityState.MOVING)
