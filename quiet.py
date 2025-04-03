# quiet.py
from __future__ import annotations
import simpy
import random
import math

# -----------------------------
# Adaptive (Actuated) Traffic Light
# -----------------------------
class FTrafficLight:
    def __init__(self, env: simpy.Environment, road: FRoad,
                 red_time: float = 15, green_time: float = 15,
                 red_amber_time: float = 3, amber_time: float = 3,
                 colour: str = "RED"):
        self.env = env
        self.road = road
        self.colour = colour
        self.red_time = red_time
        self.green_time = green_time
        self.red_amber_time = red_amber_time
        self.amber_time = amber_time
        self.last_change = env.now
        self.name = road.name  # Name light after its road.
        # Start the light cycle process.
        self.action = env.process(self.run())
    
    def actuate_timing(self):
        """
        Adjusts green time dynamically based on the current queue length.
        For example, a higher vehicle count increases green time.
        """
        q_len = self.road.get_queue_length()
        # Example dynamic calculation: base 15 seconds plus 2 sec per queued vehicle, capped at 30.
        self.green_time = min(15 + q_len * 2, 30)
    
    def run(self):
        """
        The traffic light cycle:
        RED → RED-AMBER → GREEN → AMBER → RED; the green phase is dynamically adjusted.
        """
        while True:
            self.last_change = self.env.now
            self.actuate_timing()  # Adapt the green time based on current pressure.
            
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


# -----------------------------
# Junction for Actuated System
# -----------------------------
class FJunction:
    def __init__(self, env: simpy.Environment, name: str,
                 end: bool = False, start: bool = False, weight: int = 1):
        self.env = env
        self.name = name
        self.traffic_lights: list[FTrafficLight] = []
        self.queue = simpy.PriorityResource(env, capacity=1)
        self.end = end
        self.start = start
        self.weight = weight
        # Optionally, maintain conflict groups for pressure calculations.
        self.conflict_groups: list[list[FTrafficLight]] = []
        # Start the actuation process.
        self.action = env.process(self.actuate_lights())
    
    def add_light(self, light: FTrafficLight, conflict_group: int | None = None):
        self.traffic_lights.append(light)
        if conflict_group is not None:
            # Ensure there is room for this group index.
            while len(self.conflict_groups) <= conflict_group:
                self.conflict_groups.append([])
            self.conflict_groups[conflict_group].append(light)
    
    def actuate_lights(self):
        """
        Every 5 seconds, re-assess pressures in conflict groups (or individually) 
        and set the light(s) with the highest queue pressure to green, the others to red.
        """
        while True:
            if self.start:
                # For starting junction, skip actuation.
                yield self.env.timeout(5)
                continue
            if self.conflict_groups:
                # Compute pressure for each conflict group.
                pressures = [
                    sum(light.road.get_queue_length() for light in group)
                    for group in self.conflict_groups
                ]
                best_group_index = pressures.index(max(pressures))
                for idx, group in enumerate(self.conflict_groups):
                    if idx == best_group_index:
                        # Adjust green time based on the pressure (for each light in the winning group).
                        for light in group:
                            light.green_time = min(15 + sum(light.road.get_queue_length() for light in group) * 2, 30)
                            light.colour = "GREEN"
                    else:
                        for light in group:
                            light.colour = "RED"
            else:
                if self.traffic_lights:
                    best = max(self.traffic_lights, key=lambda l: l.road.get_queue_length())
                    for light in self.traffic_lights:
                        if light == best:
                            light.green_time = min(15 + best.road.get_queue_length() * 2, 30)
                            light.colour = "GREEN"
                        else:
                            light.colour = "RED"
            yield self.env.timeout(5)


# -----------------------------
# Road Class for Both Systems
# -----------------------------
class FRoad:
    def __init__(self, name: str, speed: int, distance: int,
                 junction_start: FJunction, junction_end: FJunction,
                 car_queue: simpy.Store):
        self.name = name
        self.speed = speed
        self.distance = distance
        self.junction_start = junction_start
        self.junction_end = junction_end
        self.car_queue = car_queue
        self.traffic_light: FTrafficLight | None = None
    
    def get_queue_length(self) -> int:
        return len(self.car_queue.items)


# -----------------------------
# Car Class for Actuated Model
# -----------------------------
class FCar:
    def __init__(self, env: simpy.Environment, name: str, road: FRoad,
                 roads: list[FRoad], reaction_time: float = 1.0,
                 acceleration: float = 3.5, decceleration: float = -8.1,
                 length: float = 4.9):
        self.env = env
        self.name = name
        self.road = road           # Current road.
        self.roads = roads         # Available roads for route selection.
        self.reaction_time = reaction_time
        self.acceleration = acceleration
        self.decceleration = decceleration
        self.length = length
        self.junction_passes = 0   # Count of junctions passed.
        self.wait_time = 0         # Total accumulated waiting time.
        self.speed = road.speed    # Current speed (initialized to the road's speed).
    
    def run(self):
        """
        Process of a car:
         - Enter a road's queue.
         - Wait (accumulating wait time) until the light is green and it's at the head of the queue.
         - Include an additional start delay once conditions are met.
         - Traverse the road (for now, using a placeholder travel time).
         - Update statistics and choose the next road.
        """
        distance = self.road.distance
        while True:
            # Enter the road queue.
            yield self.road.car_queue.put(self)
            
            # Request permission to pass the junction.
            with self.road.junction_start.queue.request(priority=1) as request:
                yield request
                
                # Wait until the light is favorable and the car is first in the queue.
                while (self.road.traffic_light.colour in ["RED", "RAMBER", "AMBER"]
                       or self.road.car_queue.items[0] != self):
                    delay = sample_reaction_time(mean=self.reaction_time, std=0.2)
                    self.wait_time += delay
                    yield self.env.timeout(delay)
                
                # Extra start delay upon green signal.
                start_delay = sample_reaction_time(mean=0.8, std=0.1, lower=0.5, upper=1.0)
                self.wait_time += start_delay
                yield self.env.timeout(start_delay)
            
            # Placeholder travel time; here you would calculate acceleration/deceleration etc.
            travel_time = 5  # Replace with a kinematics-based computation if desired.
            yield self.env.timeout(travel_time)
            
            # Update statistics.
            self.junction_passes += 1
            # Choose the next road. In this simplified example, pick a random available road.
            possible_roads = [road for road in self.roads if road.junction_start == self.road.junction_end]
            if not possible_roads:
                break  # End if no further roads are available.
            self.road = random.choice(possible_roads)
            distance = self.road.distance
            

# -----------------------------
# Helper Function for Reaction Time (if not using uniform)
# -----------------------------
def sample_reaction_time(mean=1.0, std=0.2, lower=0.5, upper=1.5) -> float:
    # For demonstration, this uses a simple uniform distribution.
    # Alternatively, a truncated normal distribution can be used.
    return random.uniform(lower, upper)

