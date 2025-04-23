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
            # Ensure the conflict groups list is large enough.
            while len(self.conflict_groups) <= conflict_group:
                self.conflict_groups.append([])
            self.conflict_groups[conflict_group].append(light)
    
    def actuate_lights(self):
        """
        Dynamically adjust lights based on pressures, limiting total cycle time
        and redistributing green/red times across conflicting groups.
        """
        baseline_cycle_time = 60  # Base total cycle time (seconds)
        max_cycle_time = 120      # Max cycle cap (seconds)
        scaling_factor = 2        # Pressure scaling factor
        
        while True:
            if self.conflict_groups:
                pressures = [
                    sum(light.road.get_queue_length() for light in group)
                    for group in self.conflict_groups
                ]
                avg_pressure = sum(pressures) / len(self.conflict_groups)
                total_cycle_limit = min(max_cycle_time, baseline_cycle_time + scaling_factor * avg_pressure)
                
                total_green_time = sum(sum(light.green_time for light in group) for group in self.conflict_groups)
                total_fixed_time = sum(sum(light.red_time + light.amber_time + light.red_amber_time for light in group)
                                        for group in self.conflict_groups)
                if total_green_time + total_fixed_time > total_cycle_limit:
                    scale_factor = (total_cycle_limit - total_fixed_time) / total_green_time
                    for group in self.conflict_groups:
                        for light in group:
                            light.green_time *= scale_factor
                            light.green_time = max(10, light.green_time)
                for idx, group in enumerate(self.conflict_groups):
                    for light in group:
                        if idx == pressures.index(max(pressures)):
                            continue
                        else:
                            light.red_time += scale_factor * 2
                            light.red_time = max(10, min(40, light.red_time))
            yield self.env.timeout(5)  # Reevaluate every 5 seconds.

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
# Car Class (Restored Kinematics merged with Actuated Version)
# -----------------------------
class FCar:
    def __init__(self, env: simpy.Environment, name: str, road: FRoad,
                 roads: list[FRoad], reaction_time: float = 1.0,
                 acceleration: float = 3.5, decceleration: float = -8.1,
                 length: float = 4.9):
        self.env = env
        self.name = name
        self.road = road
        self.roads = roads
        self.reaction_time = reaction_time
        self.acceleration = acceleration
        self.decceleration = decceleration
        self.length = length
        self.junction_passes = 0
        self.wait_time = 0
        self.speed = road.speed  # initial speed
        
    def run(self):
        """
        Process for a car using the restored kinematics:
          - The car enters a road queue and waits until the light is green, 
            it is first in queue, and there is sufficient space.
          - Once allowed, it calculates:
            - v_max based on the distance available;
            - total_tG (green travel time) and new_speed.
            - Then calculates an intermediate speed v_p for deceleration, 
              and total_tR (red-phase travel time).
          - It simulates the traffic light cycle to decide whether it will proceed 
            under green or be forced to stop.
          - The car then waits the computed travel time, splits into two halves.
          - Finally, it updates its current road by choosing a possible next road.
        """
        distance = self.road.distance
        while True:
            yield self.road.car_queue.put(self)
            with self.road.junction_start.queue.request(priority=1) as request:
                yield request
                # Wait until the light is not red/ambers and self is first in queue.
                while (self.road.traffic_light.colour in ["RED", "RAMBER", "AMBER"] or 
                       self.road.car_queue.items[0] != self):
                    delay = sample_reaction_time(mean=self.reaction_time, std=0.2)
                    self.wait_time += delay
                    yield self.env.timeout(delay)
                
                # Extra start delay.
                start_delay = sample_reaction_time(mean=0.8, std=0.1, lower=0.5, upper=1.0)
                self.wait_time += start_delay
                yield self.env.timeout(start_delay)
            
            # Kinematics computation:
            # Adjust distance based on the occupancy of the road.
            for car in self.road.car_queue.items:
                distance -= car.length
            
            v_max = math.sqrt(self.speed**2 + 2 * self.acceleration * distance)
            if v_max <= self.road.speed:
                total_tG = (v_max - self.speed) / self.acceleration
                new_speed = v_max
            else:
                s_1 = (self.road.speed**2 - self.speed**2) / (2 * self.acceleration)
                s_c = distance - s_1
                t_1 = (self.road.speed - self.speed) / self.acceleration
                t_c = s_c / self.road.speed
                total_tG = t_1 + t_c
                new_speed = self.road.speed
            
            final_v = 0
            v_p = math.sqrt((self.decceleration * self.speed**2 - self.acceleration * final_v**2 + 2 * self.acceleration * self.decceleration) / (self.decceleration - self.acceleration))
            if v_p > self.road.speed:
                s_1 = (self.road.speed**2 - self.speed**2) / (2 * self.acceleration)
                s_2 = (final_v - self.road.speed**2) / (2 * self.decceleration)
                s_c = distance - s_1 - s_2
                t_1 = (self.road.speed - self.speed) / self.acceleration
                t_c = s_c / self.road.speed
                t_2 = (self.road.speed - final_v) / abs(self.decceleration)
                total_tR = t_1 + t_c + t_2
            else:
                t_1 = (v_p - self.speed) / self.acceleration
                t_2 = (final_v - v_p) / self.decceleration
                total_tR = t_1 + t_2
            
            colour = self.road.traffic_light.colour
            t = self.env.now - self.road.traffic_light.last_change
            while t < total_tR:
                match colour:
                    case "RED":
                        colour = "RAMBER"
                        t += self.road.traffic_light.red_amber_time
                    case "RAMBER":
                        colour = "GREEN"
                        t += self.road.traffic_light.green_time
                    case "GREEN":
                        colour = "AMBER"
                        t += self.road.traffic_light.amber_time
                    case "AMBER":
                        colour = "RED"
                        t += self.road.traffic_light.red_time
            
            if colour in ["RED", "RAMBER"]:
                travel_time = total_tR
                self.speed = 0
            else:
                travel_time = total_tG
                self.speed = new_speed
            
            yield self.env.timeout(travel_time / 2)
            yield self.env.timeout(travel_time / 2)
            
            distance = 0
            for car in self.road.car_queue.items:
                distance += car.length
            # Choose next road.
            next_junction = self.road.junction_end
            possible_roads = [
                road for road in self.roads 
                if road.junction_start == next_junction and 
                   (sum(car.length for car in road.car_queue.items) + self.length < road.distance) and
                   (not road.junction_end.start)
            ]
            weights = [road.junction_end.weight for road in possible_roads]
            total_weight = sum(weights)
            probabilities = [weight/total_weight for weight in weights]
            self.road = random.choices(possible_roads, probabilities)[0]
            distance += self.road.distance

# -----------------------------
# Helper for Reaction Time Sampling.
# -----------------------------
def sample_reaction_time(mean=1.0, std=0.2, lower=0.5, upper=1.5) -> float:
    # For demonstration, using a uniform distribution between lower and upper.
    return random.uniform(lower, upper)

