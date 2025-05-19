from enum import Enum
import logging
import time

from coppeliasim_zmqremoteapi_client import RemoteAPIClient

from Code.sliding_solar_panel import deploy_solar_panels, retract_solar_panels
from Code.day_night_cycle import DayNightCycle
from Code.move_arm import deploy_arm, retract_arm


def multiton(cls):
    instances = {}

    def getinstance(rover_ref, id):
        if id not in instances:
            instances[id] = cls(rover_ref, id)
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
    UPDATE_INTERVAL_SECS = 1
    MIN_CAPACITY = 0
    MAX_CAPACITY = 100
    # rates per tick
    BATTERY_CHANGE_RATES = {
        ActivityState.IDLE: -1,
        ActivityState.MOVING: -5,
        ActivityState.WORKING: -3,
        ActivityState.CHARGING: 10,
    }

    def __init__(self):
        self._last_tick_time = 0
        self._charge = 100

    def _clamp_charge(self):
        self._charge = max(
            Battery.MIN_CAPACITY, min(self._charge, Battery.MAX_CAPACITY)
        )

    def is_empty(self):
        return self._charge == Battery.MIN_CAPACITY

    def is_full(self):
        return self._charge == Battery.MAX_CAPACITY

    def _is_timeout(self):
        current_time = time.time()
        return current_time - self._last_tick_time < self.UPDATE_INTERVAL_SECS


    def tick(self, id, activity_state: ActivityState, has_charging_conditions: bool):
        if self._is_timeout():
            return

        self._last_tick_time = time.time()
        prev_charge = self._charge
        if activity_state == ActivityState.CHARGING and not has_charging_conditions:
            pass
        else:
            self._charge += Battery.BATTERY_CHANGE_RATES[activity_state]

        self._clamp_charge()
        # logging.info(
        #     f"[{id}] Battery tick -- state: {activity_state.value}, can_charge: {has_charging_conditions} | {prev_charge} -> {self._charge}"
        # )


@multiton
class RoverState:
    def __init__(self, rover_ref, id):
        self._rover_ref = rover_ref
        # The id should match the parameters passed to solar panel functions
        self._id = id
        # Default states
        self._panel_state = PanelState.HIDDEN
        self._activity_state = ActivityState.IDLE
        self._prev_action = None
        # Battery
        self._battery = Battery()

    def battery(self):
        return self._battery

    def has_charging_conditions(self):
        return DayNightCycle().is_day() and self._panel_state == PanelState.EXTENDED

    def is_charging(self):
        return self._activity_state == ActivityState.CHARGING

    def activity_state(self):
        return self._activity_state

    def is_forced_idle(self):
        return self.activity_state() == ActivityState.CHARGING or self.battery().is_empty()

    def set_activity_state(self, activity_state: ActivityState):
        id = self._id
        prev_state = self._activity_state
        state_changed_to = lambda state: prev_state != state and activity_state == state
        state_changed_from = lambda state: prev_state == state and activity_state != state

        if state_changed_to(ActivityState.CHARGING):
            self._rover_ref.deploy_rover_panel()
            self._panel_state = PanelState.EXTENDED
        elif state_changed_from(ActivityState.CHARGING):
            self._rover_ref.retract_rover_panel()
            self._panel_state = PanelState.HIDDEN

        if state_changed_to(ActivityState.WORKING):
            self._rover_ref.deploy_rover_arm()
            logging.info(f"[{id}] Starting work; deploying arm.")
        elif state_changed_from(ActivityState.WORKING):
            self._rover_ref.retract_rover_arm()
            logging.info(f"[{id}] Stopping work; retracting arm.")

        self._activity_state = activity_state

        if activity_state in [ActivityState.MOVING, ActivityState.WORKING]:
            self._prev_action = activity_state

        logging.info(
            f"[{id}] Set activity state: {prev_state}->{self._activity_state}."
        )

        return self

    def __maybe_update_state(self):
        id = self._id
        if self.battery().is_empty() and self._activity_state in [ActivityState.MOVING, ActivityState.WORKING]:
            logging.info(
                f"[{id}] Battery has run out, changing state to {ActivityState.IDLE} until recharged."
            )
            self.set_activity_state(ActivityState.IDLE)

        if self._battery.is_empty() and self._activity_state != ActivityState.CHARGING:
            if not DayNightCycle().is_day():
                return self

            logging.info(
                f"[{id}] Starting recharging; deploying solar panels."
            )
            self.set_activity_state(ActivityState.CHARGING)
            return self

        if self._activity_state == ActivityState.CHARGING:
            if self._battery.is_full():
                logging.info(
                    f"[{id}] Battery recharged; removing the '{ActivityState.CHARGING}' state; retracting solar panels."
                )
            elif not DayNightCycle().is_day():
                logging.info(
                    f"[{id}] The sun is gone; removing the '{ActivityState.CHARGING}' state; retracting solar panels."
                )
            else:
                return self

            if self._prev_action:
                logging.info(
                    f"[{id}] Returning to previous action: '{self._prev_action}'"
                )
                self.set_activity_state(self._prev_action)
            return self

        return self

    def update(self):
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

    client = RemoteAPIClient()
    sim = client.require('sim')
    sim.startSimulation()

    rover_state = RoverState("Rover0").set_activity_state(ActivityState.MOVING)
