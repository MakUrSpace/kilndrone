import json
from datetime import datetime
from dataclasses import asdict
from groundplane.things import thing

from kilndrone import KilnDrone, KilnObservation
import pandas as pd
import matplotlib.pyplot as plt


class kilndrone_thing(thing):
    def __init__(self, SORT, DEVICE_TYPE):
        super().__init__(SORT, DEVICE_TYPE)

        self.kilnDrone = KilnDrone()
        self.kilnDrone.setTargetTemperature(0)

    def state(self):
        cyclesAgo = 10
        return {"state": json.dumps(asdict(self.kilnDrone.controller.characterizeKiln())),
                "pastStates": json.dumps([asdict(s) for s in self.kilnDrone.states[:cyclesAgo]]),
                "TIMESTAMP": datetime.utcnow().isoformat()}

    def request_state(self, requested_state):
        print(requested_state)
        requestedTemperature = requested_state.get("temperature", None)
        self.request_temperature(requestedTemperature)

    def request_temperature(self, targetTemperature):
        self.kilnDrone.setTargetTemperature(targetTemperature)

    @classmethod
    def statesAsDataframe(cls, statesAsListOfDicts):
        return pd.DataFrame([asdict(KilnObservation(**state)) for state in statesAsListOfDicts])

    @classmethod
    def renderKilnDrone(cls, dataframeOfStates):
        dataframeOfStates['timestamp'] = pd.to_datetime(dataframeOfStates['timestamp'])
        dataframeOfStates = dataframeOfStates.groupby(['timestamp']).median()

        ax = dataframeOfStates[
            ['temperature', 'target', 'setPower', 'power']
        ].plot(
            secondary_y=['setPower', 'power']
        )

        ax.set_ylabel("Temperature (*F)")
        ax.right_ax.set_ylabel("Power Duty Cycle %")
        plt.xlabel("Timestamp")
        plt.title("Kilndrone State over Time")

        plt.show()
