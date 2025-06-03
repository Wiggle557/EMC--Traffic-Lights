# fixed.py
from __future__ import annotations
from quiet import FJunction  # Assuming FJunction is defined in quiet.py
import simpy

# We assume that FRoad (and related classes) are defined in your quiet.py file.
# If needed, you can import FRoad here:
# from quiet import FRoad


class FTrafficLightFixed:
    """
    This fixed timing traffic light runs through its phases in a fixed cycle.
    The timings come from predetermined parameters (for example, imported from a CSV).
    """

    def __init__(
        self,
        env: simpy.Environment,
        road: FRoad,
        red_time: float,
        green_time: float,
        red_amber_time: float,
        amber_time: float,
        colour: str = "RED",
    ):
        self.env = env
        self.road = road
        self.colour = colour
        self.red_time = red_time
        self.green_time = green_time
        self.red_amber_time = red_amber_time
        self.amber_time = amber_time
        self.last_change = env.now
        self.name = road.name  # Name the light after the road it controls.
        self.action = env.process(self.run())

    def run(self):
        """
        A simple, fixed cyclical controller.
        This cycle always goes through RED → RED-AMBER → GREEN → AMBER → RED.
        """
        while True:
            self.last_change = self.env.now
            if self.colour == "RED":
                self.colour = "RAMBER"
                yield self.env.timeout(self.red_amber_time)
            elif self.colour == "RAMBER":
                self.colour = "GREEN"
                yield self.env.timeout(self.green_time)
            elif self.colour == "GREEN":
                self.colour = "AMBER"
                yield self.env.timeout(self.amber_time)
            elif self.colour == "AMBER":
                self.colour = "RED"
                yield self.env.timeout(self.red_time)


class FJunctionFixed(FJunction):
    """
    A junction class for use with fixed-timing signals.
    It omits the dynamic actuation logic (i.e. no force_red/force_green commands).
    Instead, the traffic lights run on their own fixed cycle.
    """

    def __init__(
        self, env, name: str, end: bool = False, start: bool = False, weight=1
    ):
        # Use the same initialization as FJunction.
        super().__init__(env, name, end, start, weight)

    def actuate_lights(self):
        """
        Override the dynamic actuation so that it does nothing.
        The FTrafficLightFixed objects will just follow their own fixed cycles.
        """
        while True:
            # Simply wait for a period—or you might log that no actuation occurs.
            yield self.env.timeout(5)
