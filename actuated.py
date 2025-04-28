# actuated.py
import simpy

class ATrafficLightActuated:
    """
    A basic actuated traffic light for simulation purposes.
    
    This class is a simple cyclical traffic light. In a more sophisticated model,
    you might incorporate sensor input and dynamic adjustments.
    
    Attributes:
      - env: The simpy environment.
      - road: The road object this traffic light is attached to.
      - red_time, green_time, red_amber_time, amber_time: Phase durations.
      - colour: Current phase as a string.
    """
    def __init__(self, env, road, red_time, green_time, red_amber_time, amber_time, initial_state="RED"):
        self.env = env
        self.road = road
        self.red_time = red_time
        self.green_time = green_time
        self.red_amber_time = red_amber_time
        self.amber_time = amber_time
        self.colour = initial_state.upper()
        # Start the traffic light process.
        self.process = env.process(self.run())
        self.last_change = 0

    def run(self):
        """
        Simple cyclical behavior:
          - If in RED, after red_time change to RED_AMBER, then after red_amber_time, change to GREEN.
          - If in GREEN, after green_time change to AMBER, then after amber_time, change to RED.
        """
        while True:
            if self.colour == "RED":
                yield self.env.timeout(self.red_time)
                self.colour = "RED_AMBER"
                yield self.env.timeout(self.red_amber_time)
                self.colour = "GREEN"
            elif self.colour == "GREEN":
                yield self.env.timeout(self.green_time)
                self.colour = "AMBER"
                yield self.env.timeout(self.amber_time)
                self.colour = "RED"
            elif self.colour == "AMBER":
                yield self.env.timeout(self.amber_time)
                self.colour = "RED"
            elif self.colour == "RED_AMBER":
                yield self.env.timeout(self.red_amber_time)
                self.colour = "GREEN"
